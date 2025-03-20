'''save/load from ADIOS routines

-------
'''

from omas.omas_utils import *
from omas.omas_core import ODS

from effis.runtime import EffisLogger


def ScopeName(scope, key):
    """
    Internal function to set the group/variable name, in ADIOS slash-separated hierarchy

    :param scope: Current group hierarchy location

    :param key: Current keyword within group
    """
    newscope = str(key)
    if scope is not None:
        newscope = os.path.join(scope, newscope)
    return newscope


def TypeWrite(scopename, item, stream, tmp={}):
    #scopename = "{0}.{1}".format(ods.location.replace(top, t), key)
    #item = ods[key]

    arr = False
    test = None
    
    if item is None:
        tmp[scopename] = '_None'
    elif isinstance(item, (numpy.bytes_, numpy.str_)):
        tmp[scopename] = str(item)
    elif isinstance(item, (list, tuple)):
        tmp[scopename] = numpy.array(item)
    elif isinstance(item, (numpy.ndarray, str, float, int)):
        test = item

    if test is None:
        EffisLogger.Debug("TypeWrite: {0}".format(type(item)))
        test = tmp[scopename]


    if isinstance(test, numpy.ndarray):
        arr = True

        if test.dtype.kind in ("S", "U"):
            # I need to figure out what I should do here
            # -- Could do lists_as_dicts
            # -- Something with attributes, which isn't timestepable, but nothing in OMAS is operating like ADIOS time steps
            raise TypeError("ADIOS doesn't have string array variables")

        elif test.dtype.name.lower().startswith('o'):
            if is_uncertain(test):
                varname = '{0}_error_upper'.format(scopename)
                tmp[varname] = std_devs(test)
                stream.write(varname, tmp[varname], tmp[varname].shape, numpy.zeros(tmp[varname].ndim, dtype=numpy.int64), tmp[varname].shape)
                tmp[scopename] = nominal_values(test)
                test = tmp[scopename]
            else:
                EffisLogger.Warning("Skipping {0}: Don't know how to write Object type".format(scopename))
                #continue
                return

    if arr:
        stream.write(scopename, test, list(test.shape), numpy.zeros(test.ndim, dtype=numpy.int64).tolist(), list(test.shape))
    else:
        stream.write(scopename, test)


def MatchWrite(ods, stream, tmp={}, first=True):

    for key in ods.keys():
        
        if isinstance(ods[key], ODS):
            #RecurseWrite(ods[key], stream, tmp=tmp, first=False)
            continue
        else:
            scopename = "{0}.{1}".format(ods.location, key)
            item = ods[key]
            if isinstance(item, numpy.ndarray) and (ods["time"].shape[-1] == item.shape[-1]):
                EffisLogger.Debug("MatchWrite --- {0} {1}".format(scopename, item.shape))

            """
            for step in range(item.shape[-1]):
                #TypeWrite(scopename, item, stream, tmp={})
            """



def RecurseWrite(ods, stream, tmp={}, first=True, top=""):

    if first:
        stream.begin_step()
        top = ods.location

    for key in ods.keys():
        if isinstance(ods[key], ODS):
            RecurseWrite(ods[key], stream, tmp=tmp, first=False, top=top)
        else:
            t = '.'.join(top.split('.')[:-1])
            scopename = "{0}.{1}".format(ods.location.replace(top, t), key)
            item = ods[key]

            TypeWrite(scopename, item, stream, tmp={})

    if first:
        stream.end_step()


def TimeBlockGroupWrite(ods, stream, tmp={}, top=""):
    for key in ods.keys():
        item = ods[key]
        if isinstance(item, ODS):
            TimeBlockGroupWrite(item, stream, tmp=tmp, top=top)
        else:
            t = '.'.join(top.split('.')[:-1])
            scopename = "{0}.{1}".format(ods.location.replace(top, t), key)
            TypeWrite(scopename, item, stream, tmp=tmp)


def OtherTimeBlockGroupWrite(ods, stream, blocks, nonblocks, tmp={}, top=""):
    for key in ods.keys():
        EffisLogger.Debug("OtherTimeBlockGroupWrite -  {0} {1}".format(key, type(ods[key])))
        item = ods[key]
        if isinstance(item, ODS):
            found = False
            for block in blocks:
                if item.ulocation.find(block) != -1:
                    found = True
            if found:
                continue
            OtherTimeBlockGroupWrite(item, stream, blocks, nonblocks, tmp=tmp, top=top)
        else:
            # Not sure I want to write time here
            scopename = "{0}.{1}".format(ods.location, key)
            TypeWrite(scopename, item, stream, tmp=tmp)


def TimeBlockGroups(SubTable, blocks, nkeys, nonblocks, others, stream):

    '''
    if nkeys < 1:
        return
    '''

    tmp = {}
    OtherTimeBlockGroupWrite(SubTable, stream, blocks, nonblocks, tmp=tmp)
    EffisLogger.Debug("Between OtherTimeBlockGroupWrite")
    OtherTimeBlockGroupWrite(SubTable, stream, blocks, others, tmp=tmp)

        
    for i in range(nkeys):
        stream.begin_step()
    
        for block in blocks:
            keys = SubTable[block].keys()
            item = SubTable[block][keys[i]]
            top = item.location
            TimeBlockGroupWrite(item, stream, tmp=tmp, top=top)

        for nonblock in nonblocks:
            pass

        stream.end_step()



def GetTimeBlocks(ods, first=True, timeblocks=[], timenonblocks=[], others=[]):

    pattern = re.compile("^\d+$")
    KeepKeys = []

    for key in ods.keys():
        if isinstance(key, int):
            if (key > 0):
                continue
        elif type(key) is str:
            match = pattern.match(key)
            if (match is not None) and (int(match.group()) > 0):
                continue
        else:
            raise ValueError("Unhandled type for {0}: {1}".format(key, type(key)))
        
        KeepKeys += [key]

      
    for key in KeepKeys:
        if isinstance(ods[key], ODS):
            GetTimeBlocks(ods[key], first=False, timeblocks=timeblocks, timenonblocks=timenonblocks, others=[])
        else:
            if (key == "time") and ods.ulocation.endswith('.:'):
                #timeblocks += [ods.ulocation]
                #timeblocks += ['.'.join(ods.ulocation.split(".")[:-1])]
                timeblocks += ['.'.join(ods.ulocation.split(".")[1:-1])]
            elif key == "time":
                timenonblocks += [ods.location]
            else:
                others += [ods.location]

    return timeblocks, timenonblocks, others


def ods2adios(ods, outpath):
    import adios2

    if not isinstance(ods, ODS):
        raise TypeError("Can only save ADIOS from top-level or IMAS-group level ODS object")

   
    # First determine if this is top-level or single IMAS group to save
    if ods.parent is None:
        TableNames = ods.keys()
    else:
        TableNames = [ods.location]
        

    for TableName in TableNames:

        if ods.parent is None:
            SubTable = ods[TableName]
        else:
            SubTable = ods


        if not SubTable.homogeneous_time():
            EffisLogger.Warning("Skipping {SubTable}, not homogeneous_time".format(SubTable=SubTable))
            continue

        ioname = TableName
        adios = adios2.Adios()
        io = adios.declare_io(ioname)

        if not os.path.exists(outpath):
            os.makedirs(outpath)
        filepath = os.path.join(outpath, "{TableName}.bp".format(TableName=TableName))

        with adios2.Stream(io, filepath, "w") as stream:

            # Next get the block time steps
            blocks, nonblocks, others = GetTimeBlocks(SubTable, timeblocks=[], timenonblocks=[], others=[])
            EffisLogger.Debug("others: {0}".format(others))
            EffisLogger.Debug("timeblocks: {0}".format(blocks))

            nkeys = 0
            for i in range(len(blocks)):
                """
                if i == 0:
                    keys0 = SubTable[blocks[0]].keys()
                pathi = '.'.join(blocks[i].split(".")[1:])
                """
                if SubTable[blocks[i]].keys() != SubTable[blocks[0]].keys():
                    EffisLogger.RaiseError(ValueError, "{0} {1}".format(TableName, blocks) + "\n" + "I don't know why this is happening with homogeneous_time")
                nkeys = len(SubTable[blocks[0]].keys())

            """
            for block in blocks:
                path = block.split(".")
                print(TableName, block, SubTable[block].keys())
                #path = '.'.join(path[1:])
                for key in SubTable[block]:
                    RecurseWrite(SubTable[block][key], stream)
            """

            TimeBlockGroups(SubTable, blocks, nkeys, nonblocks, others, stream)


            '''
            for nonblock in nonblocks:
                path = nonblock.split(".")
                path = '.'.join(path[1:])
                MatchWrite(SubTable[path], stream)
                """
                for key in SubTable[path]:
                    if type(SubTable[path][key]) is numpy.ndarray:
                        if path.find('.') != -1:
                            print("HERE ---", nonblock, path, key, SubTable[path][key].shape)
                """
            '''

        EffisLogger.Info("Wrote {0}".format(filepath))

    return



def dict2adios(filename, dictin, scope=None, recursive=True, lists_as_dicts=False, compression=None, io=None, stream=None, tmp=None):
    """
    Utility function to save hierarchy of dictionaries containing numpy-compatible objects to BP file

    :param filename: BP file to save to

    :param dictin: input dictionary

    :param scope: group to save the data in

    :param recursive: traverse the dictionary

    :param lists_as_dicts: convert lists to dictionaries with integer strings

    :param compression: gzip compression level

    :param io: ADIOS I/O object

    :param stream: ADIOS Stream object

    :param temp: holds things not to go out of scope for ADIOS writing
    """
    import adios2


    if (io is None) and (stream is None) and isinstance(filename, str):
        ioname = os.path.splitext(os.path.basename(filename))[0]
        adios = adios2.Adios()
        io = adios.declare_io(ioname)
        with adios2.Stream(io, os.path.join(os.path.dirname(filename), "{0}.bp".format(ioname)), "w") as stream:
            stream.begin_step()
            dict2adios(filename, dictin, recursive=recursive, lists_as_dicts=lists_as_dicts, compression=compression, io=io, stream=stream, tmp={})
            stream.end_step()
        return

    if isinstance(dictin, ODS):
        dictin = dictin.omas_data


    for key, item in list(dictin.items()):

        if isinstance(item, ODS):
            item = item.omas_data

        scopename = ScopeName(scope, key)


        if isinstance(item, dict):
            if recursive:
                dict2adios(filename, item, scope=scopename, recursive=recursive, lists_as_dicts=lists_as_dicts, compression=compression, io=io, stream=stream, tmp=tmp)

        elif lists_as_dicts and isinstance(item, (list, tuple)) and not isinstance(item, numpy.ndarray):
            """
            Making lists a dictionaries indexed like "0", "1", ... isn't something very BP-like, and I turned it off by default
            """
            item = {'%d' % k: v for k, v in enumerate(item)}
            dict2adios(filename, item, scope=scopename, recursive=recursive, lists_as_dicts=lists_as_dicts, compression=compression, io=io, stream=stream, tmp=tmp)

        else:

            arr = False
            test = None
            
            if item is None:
                tmp[scopename] = '_None'
            elif isinstance(item, (numpy.bytes_, numpy.str_)):
                tmp[scopename] = str(item)
            elif isinstance(item, (list, tuple)):
                tmp[scopename] = numpy.array(item)
            elif isinstance(item, (numpy.ndarray, str, float, int)):
                test = item

            if test is None:
                test = tmp[scopename]


            if isinstance(test, numpy.ndarray):
                arr = True

                if test.dtype.kind in ("S", "U"):
                    # I need to figure out what I should do here
                    # -- Could do lists_as_dicts
                    # -- Something with attributes, which isn't timestepable, but nothing in OMAS is operating like ADIOS time steps
                    raise TypeError("ADIOS doesn't have string array variables")

                elif test.dtype.name.lower().startswith('o'):
                    if is_uncertain(test):
                        varname = '{0}_error_upper'.format(scopename)
                        tmp[varname] = std_devs(test)
                        stream.write(varname, tmp[varname], tmp[varname].shape, numpy.zeros(tmp[varname].ndim, dtype=numpy.int64), tmp[varname].shape)
                        tmp[scopename] = nominal_values(test)
                        test = tmp[scopename]
                    else:
                        EffisLogger.Warning("Skipping {0}: Don't know how to write Object type".format(scopename))
                        continue

            if arr:
                stream.write(scopename, test, list(test.shape), numpy.zeros(test.ndim, dtype=numpy.int64).tolist(), list(test.shape))
            else:
                stream.write(scopename, test)

    return


def save_omas_adios(ods, filename):
    """
    Save an ODS to BP

    :param ods: OMAS data set

    :param filename: filename or file descriptor to save to
    """
    #return dict2adios(filename, ods, lists_as_dicts=False)
    #return dict2adios(filename, ods, lists_as_dicts=True)
    return ods2adios(ods, filename)


def convertDataset(ods, handle):
    """
    Recursive utility function to map HDF5 structure to ODS

    :param ods: input ODS to be populated

    :param data: HDF5 dataset of group
    """
    import adios2

    variables = handle.available_variables()

    for varname in variables:

        if varname.endswith('_error_upper'):
            continue

        has_slice = False
        has_error = False

        errname = varname + '_error_upper'
        steps = int(variables[varname]['AvailableStepsCount'])

        if (steps > 1) and (varname.find('time_slice') != -1):
            has_slice = True
            before, after = varname.split('.time_slice.')
        if errname in variables:
            has_error = True

        arr = handle.read(varname, step_selection=[0, steps])
        if has_error:
            err = handle.read(errname, step_selection=[0, steps])


        if has_slice:
            for i in range(steps):
                v = "{0}.time_slice.{1}.{2}".format(before, i, after)
                if has_error and isinstance(err, (float, numpy.floating)):
                    ods[v] = ufloat(arr[i], err[i])
                elif has_error:
                    ods[v] = uarray(arr[i], err[i])
                else:
                    #ods.setraw(v, arr[i])
                    ods[v] = arr[i]

        else:

            if has_error:
                if isinstance(err, (float, numpy.floating)):
                    ods[varname] = ufloat(arr, err)
                else:
                    ods[varname] = uarray(arr, err)
            else:
                #ods.setraw(varname, arr)
                ods[varname] = arr



def load_omas_adios(filename, consistency_check=False, imas_version=omas_rcparams['default_imas_version'], cls=ODS):
    """
    Load ODS or ODC from BP

    :param filename: filename or file descriptor to load from

    :param consistency_check: verify that data is consistent with IMAS schema

    :param imas_version: imas version to use for consistency check

    :param cls: class to use for loading the data

    :return: OMAS data set
    """

    import adios2

    ods = cls(imas_version=imas_version, consistency_check=consistency_check)
    with adios2.FileReader(filename) as data:
        convertDataset(ods, data)
    ods.consistency_check = consistency_check

    for name in (
        'equilibrium.time_slice.1.fsqt',
        'equilibrium.time_slice.1.time',
        'equilibrium.time_slice.1.wdot',
        'equilibrium.vacuum_toroidal_field.b0'
    ):
        EffisLogger.Debug("{0} {1}".format(name, ods[name]))
        #print(name, ods[name].dtype)
        #print(name, ods[name].values())

    return ods


def through_omas_adios(ods, method=['function', 'class_method'][1]):
    """
    Test save and load OMAS BP

    :param ods: ods

    :return: ods
    """
    filename = omas_testdir(__file__) + '/test.bp'
    ods = copy.deepcopy(ods)  # make a copy to make sure save does not alter entering ODS
    if method == 'function':
        save_omas_adios(ods, filename)
        ods1 = load_omas_adios(filename)
    else:
        ods.save(filename)
        ods1 = ODS().load(filename)
    return ods1
