####################################################################################################
# main/surface_to_ribbon.py
# The code for the function that handles the registration of retinotopy
# By Noah C. Benson

import numpy                        as     np
import scipy                        as     sp
import nibabel.freesurfer.io        as     fsio
import nibabel.freesurfer.mghformat as     fsmgh
from   math                         import pi
from   numbers                      import Number
from   pysistence                   import make_dict
from   numbers                      import Integral
import os, sys

from neuropythy.freesurfer import (freesurfer_subject, add_subject_path, find_subject_path,
                                   cortex_to_ribbon, cortex_to_ribbon_map, Hemisphere)
from neuropythy.util       import (CommandLineParser)

surface_to_ribbon_help = \
   '''
   Syntax: surface_to_ribbon <subject> <out>
   <subject> must be a valid FreeSurfer subject id (in the $SUBJECTS_DIR directory
     or directory path)
   <out> is the output MGH/MGZ file to write.
   In addition to the subject and the output filename, at least one and at most two
   surface file(s) must be specified. These may be specified using the --lh (or -l)
   and --rh (or -r) options below or without them; if they files are specified
   without the given arguments and the ordering cannot be detected by the number of
   vertices in the file, then the left hemisphere surface is assumed to be
   specified first.
   The command projects the given surface files into the subject's ribbon and
   writes the result out to the given filename. If only one hemisphere's surface
   datafile is given, then only that hemisphere's data is projected to the ribbon.

   The following options may be given:
     * -v|--verbose
       Indicates that detailed output should be printed.
     * -l|--lh=<file>
       -r|--rh=<file>
       These options specify the surface data files that are to be projected to
       the subject's ribbon.
     * -m|--method=<name>
       Specifies the method that should be used. Supported options are weighted
       (the default) or max. Both methods find the overlap between the lines from
       the white to the pial surface vertices and the individual ribbon voxels; the
       'weighted' method assigns a value to each voxel by performing a weighted
       average of the vertex values whose white-pial lines pass through it using
       the lengths of the intersecting lines as weights, while the 'max' method
       uses the longest line passing through the voxel.
     * -f|--fill=<value>
       The fill value (default: 0) is inserted in everywhere in the volume that is
       not part of the ribbon.
     * -t|--dtype=<value>
       Specifies that the output data type should be <value>. Currently supported are
       'int' or 'float' (default: 'float').
     * -d|--subjects-dir=<path>
       Specifies that the given path(s) should be added to the subjects directory
       when performing the operation. Note that this may include directories
       separated by colons (:), as with the PATH environment variable.
     * --
       This token, by itself, indicates that the arguments that remain should not
       be processed as flags or options, even if they begin with a -.
   '''
_surface_to_ribbon_parser_instructions = [
    # Flags
    ('h', 'help',         'help',         False),
    ('v', 'verbose',      'verbose',      False),
    # Options             
    ['l', 'lh',           'lh_file',      None],
    ['r', 'rh',           'rh_file',      None],
    ['f', 'fill',         'fill',         0],
    ['m', 'method',       'method',       'weighted'],
    ['t', 'type',         'dtype',        None],
    ['d', 'subjects-dir', 'subjects_dir', None]]
_surface_to_ribbon_parser = CommandLineParser(_surface_to_ribbon_parser_instructions)

def read_surf_file(flnm):
  if flnm.endswith(".mgh") or flnm.endswith(".mgz"):
    data = fsmgh.load(flnm).get_data().flatten()
  else:
    data = fsio.read_morph_data(flnm)
  return data

def surface_to_ribbon_command(args):
    '''
    surface_to_rubbon_command(args) can be given a list of arguments, such as sys.argv[1:]; these
    arguments may include any options and must include exactly one subject id and one output
    filename. Additionally one or two surface input filenames must be given. The surface files are
    projected into the ribbon and written to the output filename. For more information see the
    string stored in surface_to_ribbon_help.
    '''
    # Parse the arguments
    (args, opts) = _surface_to_ribbon_parser(args)
    # First, help?
    if opts['help']:
        print surface_to_ribbon_help
        return 1
    # and if we are verbose, lets setup a note function
    verbose = opts['verbose']
    def note(s):
        if verbose: print s
        return verbose
    # Add the subjects directory, if there is one
    if 'subjects_dir' in opts and opts['subjects_dir'] is not None:
        add_subject_path(opts['subjects_dir'])
    # figure out our arguments:
    (lhfl, rhfl) = (opts['lh_file'], opts['rh_file'])
    if len(args) == 0:
      raise ValueError('Not enough arguments provided!')
    elif len(args) == 1:
      # must be that the subject is in the env?
      sub = find_subject_path(os.getenv('SUBJECT'))
      outfl = args[0]
    elif len(args) == 2:
      sbpth = find_subject_path(args[0])
      if sbpth is not None:
        sub = sbpth
      else:
        sub = find_subject_path(os.getenv('SUBJECT'))
        if lhfl is not None: rhfl = args[0]
        elif rhfl is not None: lhfl = args[0]
        else: raise ValueError('Given arg is not a subject: %s' % args[0])
      outfl = args[1]
    elif len(args) == 3:
      sbpth0 = find_subject_path(args[0])
      sbpth1 = find_subject_path(args[1])
      if sbpth0 is not None:
        sub = sbpth0
        if lhfl is not None: rhfl = args[1]
        elif rhfl is not None: lhfl = args[1]
        else: raise ValueError('Too many arguments given: %s' % args[1])
      elif sbpth1 is not None:
        sub = sbpth1
        if lhfl is not None: rhfl = args[0]
        elif rhfl is not None: lhfl = args[0]
        else: raise ValueError('Too many arguments given: %s' % args[0])
      else:
        sub = find_subject_path(os.getenv('SUBJECT'))
        if lhfl is not None or rhfl is not None:
          raise ValueError('Too many arguments and no subject given')
        (lhfl, rhfl) = args
      outfl = args[2]
    elif len(args) == 4:
      if lhfl is not None or rhfl is not None:
          raise ValueError('Too many arguments and no subject given')
      subidx = next((i for (i,a) in enumerate(args) if find_subject_path(a) is not None), None)
      if subidx is None: raise ValueError('No subject given')
      sub = find_subject_path(args[subidx])
      del args[subidx]
      (lhfl, rhfl, outfl) = args
    else:
      raise ValueError('Too many arguments provided!')
    if sub is None: raise ValueError('No subject specified or found in $SUBJECT')
    if lhfl is None and rhfl is None: raise ValueError('No surfaces provided')
    # check the method
    method = opts['method'].lower()
    if method != 'weighted' and method != 'max':
        raise ValueError('Unsupported method: %s' % method)
    # and the datatype
    if opts['dtype'] is None: dtyp = None
    elif opts['dtype'].lower() == 'float': dtyp = np.float32
    elif opts['dtype'].lower() == 'int': dtyp = np.int32
    else: raise ValueError('Type argument must be float or int')
    # Now, load the data:
    note('Reading surfaces...')
    (lhdat, rhdat) = (None, None)
    if lhfl is not None:
        note('   - Reading LH file: %s' % lhfl)
        lhdat = read_surf_file(lhfl)
    if rhfl is not None:
        note('   - Reading RH file: %s' % rhfl)
        rhdat = read_surf_file(rhfl)
    (dat, hemi) = (rhdat, 'rh') if lhdat is None else \
                  (lhdat, 'lh') if rhdat is None else \
                  ((lhdat, rhdat), None)
    note('Generating vertex-to-voxel mapping...')
    sub = freesurfer_subject(sub)
    s2r = cortex_to_ribbon_map(sub, hemi=hemi)
    # okay, make the volume...
    note('Generating volume...')
    vol = cortex_to_ribbon(sub, dat,
                           map=s2r, hemi=hemi, method=method, fill=opts['fill'], dtype=dtyp)
    # and write out the file
    note('Exporting volume file: %s' % outfl)
    vol.to_filename(outfl)
    note('surface_to_ribbon complete!')
    return 0    

