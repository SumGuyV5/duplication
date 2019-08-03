#!/usr/bin/env python
import hashlib
import math
import os
import sys


def convert_size(size_bytes):
    """
    creates a string for with bytes into the larges byte post fix.

    :param size_bytes: is the number of bytes.
    :return: the number of bytes as a string in the larges byte post fix.
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s}, {size_name[i]}'


def query_yes_no(question, default="yes"):
    """
    Ask a yes/no question via input() and return their answer.

    :param question: is a string that is presented to the user.
    :param default: is the presumed answer if the user just hits <Enter>.
                It must be "yes" (the default), "no" or Nome (meaning
                an answer is required of the user).
    :return: value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "ye": True, "y": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f'invalid default answer: "{default}"')

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


def chunk_reader(obj, chunk_size=1024):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = obj.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(filename, first_chunk=False, algorithms=hashlib.sha1):
    """
    Opens the file and runs it through a hash algorithm.

    :param filename: name of the file to read and feed to the hashlib.
    :param first_chunk: if we should only read the first 1k of data only. default False.
    :param algorithms: what algorithm to use. default hashlib.sha1.
    :return: return the hashed object.
    """
    hash_obj = algorithms()
    file = open(filename, 'rb')

    if first_chunk:
        hash_obj.update(file.read(1024))
    else:
        for chunk in chunk_reader(file):
            hash_obj.update(chunk)
    hashed = hash_obj.digest()

    file.close()
    return hashed


def files_size(paths):
    """
    find all files in paths and group them by file size.

    :param paths: list of paths to look for duplicate files.
    :return: returns a dict of files by size.
    """
    files_size_rtn = {}
    for path in paths:
        for dir_path, dir_names, file_names in os.walk(path):
            for filename in file_names:
                full_path = os.path.join(dir_path, filename)
                size = 0
                try:
                    size = os.path.getsize(full_path)
                except OSError as e:
                    print(f'{e}')

                # we don't care about files with 0 size. move to the next.
                if size == 0:
                    continue

                duplicate = files_size_rtn.get(size)

                if duplicate:
                    files_size_rtn[size].append(full_path)
                else:
                    files_size_rtn[size] = []  # create the list for this file size.
                    files_size_rtn[size].append(full_path)
    return files_size_rtn


def hashes_dict(hash_dict, first_chunk=True):
    """
    We take a list and hash the files and put them in a groups by hash.

    :param hash_dict: this is a dict of files to be hashed.
    :param first_chunk: if True we will only hash to first 1024k.
    :return: returns a dict of files grouped by hash.
    """
    dict_rtn = {}
    for __, files in hash_dict.items():
        if len(files) < 2:
            continue  # there is only one file of this size, so no there is no need to hash. move on to the next.

        for filename in files:
            file_hash = get_hash(filename, first_chunk)

            duplicate = dict_rtn.get(file_hash)
            if duplicate:
                dict_rtn[file_hash].append(filename)
            else:
                dict_rtn[file_hash] = []  # create a list of files with matching this hash.
                dict_rtn[file_hash].append(filename)
    return dict_rtn


def delete_dir_search(hashes_full, dir_del, dir_keep):
    """
    We search through hashes_full and find any files that have a dup with one file in "dir_keep" and "dir_del" and
    add the file from "dir_del" to rtn as a list of files to delete.

    :param hashes_full: this is all the dup files.
    :param dir_del: is a directory with a file we wish to delete if a dup is found in "del_where".
    :param dir_keep: is a directory that has files we wish to keep.
    :return: is a list of files to delete found to delete.
    """
    delete_dir_list = []  # list of files found and need to be deleted.
    for key, value in hashes_full.items():
        idx_del = -1
        idx_keep = -1
        for idx, item in enumerate(value):
            if os.path.dirname(item) == dir_del:
                idx_del = idx
            elif os.path.dirname(item) == dir_keep:
                idx_keep = idx
        if idx_del > -1 and idx_keep > -1:
            delete_dir_list.append(hashes_full[key][idx_del])
            del hashes_full[key][idx_del]  # the user wish to delete this file because it has a dup.
    return delete_dir_list


def delete_dup_list(hashes_full):
    """
    Take a dictionary of all files that have hashes that collide and ass the user what to delete or keep all.

    :param hashes_full: dict of all found dup files.
    :return: returns a list of files to delete.
    """
    delete_list = []  # list of files to delete
    for key, value in hashes_full.items():
        while len(value) > 1:
            print('New Hash.')
            print(key.hex(), value)
            while True:
                try:
                    a = int(input(f'Enter a number to add that file to the delete list: '
                                  f'1 to {len(value)} or 0 to select none.')) - 1
                    if a > len(value):
                        print('Selection does not exist. Please try again.')
                    else:
                        break  # break out because we have a valid input
                except ValueError:
                    print('Not an integer value...')
            if a <= -1:
                print("Don't delete any of these duplicates.")
                break
            else:
                # if this hash has only two dup files lets ask the user
                # should we delete all dup files in the directory.
                if len(value) == 2:
                    # if the selected file is the second in the list then b = first file in the list else vice versa.
                    b = (a - 1) if a == 1 else (a + 1)
                    dir_del = os.path.dirname(value[a])  # delete files in this directory.
                    dir_keep = os.path.dirname(value[b])  # where a duplicate is found in this directory.

                    if dir_del == dir_keep:
                        print(f'File {value[a]} and file {value[b]} are in the same directory')
                    elif query_yes_no(f'Would you like to delete all file found in "{dir_del}" '
                                      f'that are also found in "{dir_keep}"?'):
                            delete_list += delete_dir_search(hashes_full, dir_del, dir_keep)
                            continue  # delete_dir_search should have removed all the files.
                file = value[a]
                del value[a]
                print(f'Ok file "{file}" is being add to the delete list.')
                delete_list.append(file)
    return delete_list


def print_size(files_dict):
    """
    Calculates the size of all files passed, added together and printed out.

    :param files_dict: dictionary of files to have there files calculated.
    :return: None
    """
    size = 0
    for key, value in files_dict.items():
        size += (os.path.getsize(value[0]) * (len(value) - 1))

    print(convert_size(size))


def print_hash(hashes):
    """
    Prints out the hash group and the connect files.

    :param hashes: dictionary of files to print out.
    :return: None
    """
    for key, value in hashes.items():
        print(key.hex(), value)
        print(os.path.dirname(value[1]))


def main(paths):
    """
    Takes the paths pass by the user. It groups all the files in those directories by size, 1Kilobyte hash and full hash.
    Then it takes all the files that have matching full hash and asks the user what files they wish to delete.

    :param paths: the paths the user passed to the program.
    :return: None
    """
    if paths:
        files_by_size = files_size(paths)
        hashes_on_1k = hashes_dict(files_by_size)
        hashes_full = hashes_dict(hashes_on_1k, False)

        # print_size(hashes_full)

        delete_list = delete_dup_list(hashes_full)
        if query_yes_no("do you really wish to delete the files you selected."):
            for x in delete_list:
                os.remove(x)
        # print(delete_list)
        # print_hash(hashes_full)
    else:
        print('Please pass the paths to check as parameters to the script')


if __name__ == "__main__":
    main(sys.argv[1:])
    # start_time = time.time()
    # main(["D:\\videos"])
    # print("--- %s seconds ---" % (time.time() - start_time))
