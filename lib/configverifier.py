#!/usr/bin/python3
###############################################################################
##
##   File Name    - Verifier.pm
##
##   Description  - A module for checking the domain specific syntax of data
##                  with regards to the structure of that data and the basic
##                  data types.
##
##                  See the POD section for further details.
##
###############################################################################
##
###############################################################################
##
##   Package      - Config::Verifier
##
##   Description  - See the POD section for further details.
##
###############################################################################
#
#
#
#


# ***** PACKAGE DETAILS *****

__all__ = ()
__version__ = '0.1'
__author__ = 'Anthony Cooper'

# ***** REQUIRED PACKAGES *****

# Standard Python packages.

import re
import sys
from copy import deepcopy
from typing import Any

# Project Python packages.

from classutils import classinstancemethod

# ***** GLOBAL DATA DECLARATIONS *****

class VerifierError(Exception):
    pass


class Verifier():
    '''
    This class....
    '''

    # ***** CLASS DATA DECLARATIONS *****

    # Constants representing the state of hashes in a syntax array.

    __ONE_HASH            = 0x01
    __SINGLE_FIELD_HASHES = 0x02
    __TYPED_FIELD_HASHES  = 0x04

    # Constants for assorted messages.

    __SCHEMA_ERROR = 'Illegal syntax element found in syntax tree '

    # Lookup hashes for converting assorted measures.

    __DURATION_IN_SECONDS = {'s' : 1,
                             'm' : 60,
                             'h' : 3_600,
                             'd' : 86_400,
                             'w' : 604_800}
    __AMOUNTS = {'B'   : 1,
                 'K'   : 1_000,
                 'M'   : 1_000_000,
                 'G'   : 1_000_000_000,
                 'T'   : 1_000_000_000_000,
                 'KB'  : 1_000,
                 'MB'  : 1_000_000,
                 'GB'  : 1_000_000_000,
                 'TB'  : 1_000_000_000_000,
                 'KiB' : 1_024,
                 'MiB' : 1_048_576,
                 'GiB' : 1_073_741_824,
                 'TiB' : 1_099_511_627_776}

    # A lookup hash containing regexes in the form or plain strings that will
    # get replaced by their compiled counterparts, whilst having their
    # non-capturing counterparts added to the %Syntax_Regexes hash below. This
    # reduces maintenance and mistakes.

    __CAPTURING_REGEXES = \
        {'amount'      : re.compile(r'^([-+]?\d+(?:\.\d+)?)([KMGT])?$'),
         'amount_data' : re.compile(r'^(\d+)((?:[KMGT]i?)?[Bb])$'),
         'duration'    : re.compile(r'^(\d+)(ms|[smhdw])$')}



    # A lookup hash for common syntactic elements. Please note the (?!.)
    # sequence at the end matches nothing, i.e. '' and undef should go to false.
    # The more complex regexes are generated at load time.

    __syntax_regexes = \
        {'anything'  : re.compile(r'^.+$'),
         'boolean'   : re.compile(r'^(?i:true|yes|y|on|1|'
                                  + r'false|no|n|off|0|(?!.))$'),
         'name'      : re.compile(r'^[-_.' + "'" + r'"()\[\] a-zA-Z0-9]+$'),
         'plugin'    : re.compile(r'^[-_.a-zA-Z0-9]+$'),
         'printable' : re.compile(r'^[^\x00-\x1f\x7f]+$'),
         'string'    : re.compile(r'^[-_. a-zA-Z0-9]+$'),
         'unix_path' : re.compile(r'^(?:(?!.*\\/|.*\000).)+$'),
         'user_name' : re.compile(r'^[-_a-zA-Z0-9]+[-_a-zA-Z0-9 ]+'
                                  + r'[-_a-zA-Z0-9]+$'),
         'variable'  : re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]+$')}

    # Decorator for class and instance methods.


    # Whether debug messages should be logged or not.

    __debug = False

    def __init__(self, syntax_tree: dict[str, Any] = None):
        self.__syntax_tree = {} if syntax_tree is None else syntax_tree
        self.__syntax_regexes = deepcopy(Verifier.__syntax_regexes)
        self.__debug = Verifier.__debug

        # Now we have an initialised internal object, check the specified syntax
        # tree for errors.

        #self.__check_syntax_tree(self.syntax_tree)

    @classmethod
    def amount_to_units(cls, value: str, want_bits: bool = False) -> float:
        units = 0
        if (not want_bits
            and (m := cls.__CAPTURING_REGEXES['amount'].search(value))) \
           or (m := cls.__CAPTURING_REGEXES['amount_data'].search(value)):
            amount = float(m.group(1))
            unit = m.group(2)
            if unit:
                units = amount * cls.__AMOUNTS[unit.replace('b', 'B')]
                given_as_bits = True if unit.endswith('b') else False
                if not given_as_bits and want_bits:
                    units *= 8
                elif given_as_bits and not want_bits:
                    units = units / 8
            else:
                units = float(amount)
        else:
            raise VerifierError(f"Invalid amount `{value}' detected.")

        return units

    @classmethod
    def duration_to_seconds(cls, duration: str) -> int | float:
        seconds = 0
        if m := cls.__CAPTURING_REGEXES['duration'].search(duration):
            amount = float(m.group(1))
            unit = m.group(2)
            if unit == 'ms':
                seconds = amount / 1000;
            else:
                seconds = int(amount * cls.__DURATION_IN_SECONDS[unit])
        else:
            raise VerifierError(f"Invalid duration `{duration}' detected.")

        return seconds

    @classinstancemethod
    def register_syntax_regex(context, name: str, regex: str):
        '''
        Hello there.
        '''

        # The name must be a simple variable like name and the regex pattern
        # must be properly anchored.

        if not re.search(r'^[-a-zA-Z0-9_.]+$', name):
            raise VerifierError \
                (f"`{name}' is not a suitable syntax element name.")
        if not re.search(r'^\^.*\$$', regex):
            raise VerifierError(f"`{regex}' is not anchored to the start and "
                                + 'end of the string.')
        if name in Verifier.__CAPTURING_REGEXES or name == 'boolean':
            raise VerifierError(f"Changing `{name}' is not permitted.")

        # Register it.

        try:
            context.__syntax_regexes[name] = re.compile(regex)
        except Exception as e:
            raise VerifierError \
                (f"Invalid regular expression `{regex}'. Error given was: {e}.")

    def __check_syntax_tree(self,
                            syntax: dict[str, Any],
                            seen:   set[int] | None = None):
        syntax_tree = {} if syntax_tree is None else syntax_tree
    
        # Guard against infinite recursion due to loops in the syntax tree
        # (which are allowed, e.g. cascading menu definitions).
    
        if id(syntax) in seen:
            return
        seen.update(id(syntax))
    
        # Check arrays, these are not only lists but also branch points.

        match syntax:

            case list():
    
                # Check for any hashes, records, making sure that if there are
                # any that they are of the correct type (one unique record, any
                # single field or typed).
    
                check_hashes_in_array(syntax)

                # Scan through the array processing each type of entry.
    
                for syn_el in syntax:
                    if not isinstance(syn_el, (dict, list)):
                        if self.__debug:
                            Verifier.__logger \
                                (f"Checking syntax tree element `{syn_el}'.")
                        self.match_syntax(syn_el)
                    else:
                        self.__check_syntax_tree(syn_el, seen)

            case dict():
                for key in syntax:
                    value = syntax[key]
                    self.match_syntax(key)
                    if not isinstance(syn_el, (dict, list)):
                        self.match_syntax(value)
                    else:
                        self.__check_syntax_tree(value, seen)

            case _:
                raise VerifierError('Syntax tree has unsupported element of '
                                    + f"type `{type(syntax)}'.")

    def __verify_node(self,
                      data:   dict[str, Any],
                      syntax: dict[str, Any],
                      path:   list[str],
                      status: list[str]):

        # Check arrays, these are not only lists but also branch points.

        if isinstance(data_type, list) and isinstance(syntax_type, list):
            self.__verify_arrays(data, syntax, path, status)

        # Check records.

        elif isinstance(data_type, dict) and isinstance(syntax_type, dict):
            self.__verify_hashes(data, syntax, path, status)

        # We have a mismatch.

        elif isinstance(syntax_type, list):
            status.append(f'The {path} field is not a list.\n')
        else:
            status.append(f'The {path} field is not a record.\n')

    def __verify_arrays(self,
                        data:   dict[str, Any],
                        syntax: dict[str, Any],
                        path:   list[str],
                        status: list[str]):

        hash_state = None

        # Scan through the array looking for a match based upon scalar values
        # and container types.

        for i, item in enumerate(data):

            # We are comparing scalar values.

            if not isinstance(entry, (dict, list)):
                errs = []
                for syn_el in syntax:
                    if not isinstance(syn_el, (dict, list)):
                        if self.__debug:
                            Verifier.__logger(f"Comparing `{path}->[{i}]:"
                                              + f"{item}' against `{syn_el}'.")
                        err = []
                        if self.match_syntax(syn_el, item, err):
                            continue
                        elif err:
                            errs.extend(err)
                else:
                    if item is None:
                        value = 'undefined value'
                    else:
                        value = f"value `{item}'"
                    if errs:
                        msg = ' (' + ' or '.join(errs) + ')'
                    status.append(f"Unexpected {value} found at {path}->[{i}]. "
                                  + "It either doesn't match the expected "
                                  + f'value format{msg}, or a list or record '
                                  + 'was expected instead.\n')

            # We are comparing arrays.

            elif isinstance(item, list):

                local_status = []

                # As we are going off piste into the unknown (arrays don't
                # really give us much clue as to what we are looking at nor
                # where decisively to go), we may need to backtrack, so use a
                # local status string and then only report anything wrong if we
                # don't find a match at all.

                for syn_el in syntax:
                    if isinstance(syn_el, list):
                        if self.__debug:
                            Verifier.__logger(f"Comparing `{path}->[{i}]:"
                                              + "(list)' against `(list)'.")
                        local_status = []
                        selff.__verify_node(item,
                                            syn_el,
                                            f'{path}->[{i}]',
                                            local_status)
                        if not local_status:
                            continue
                else:

                    # Only report an error once for each route taken through the
                    # syntax tree.

                    if not local_status:
                        status.append \
                            (f"Unexpected list found at {path}->[{i}].\n")
                    else:
                        status.append(local_status)

            # We are comparing hashes, records, so look to see if there is a
            # common field in one of the syntax hashes. If so then take that
            # branch.

            elif isinstance(item, dict):

                # If we haven't done it already, determine what type of hashes
                # we have in the syntax array (just one or multiple that are
                # typed in some way).

                if hash_state is None:
                    hash_state = Verifier.__check_hashes_in_array(syntax)

                # If there is one hash in the syntax array then that's our path.

                if hash_state == Verifier.__ONE_HASH:
                    self.__take_singular_hash_path(data,
                                                   syntax,
                                                   path,
                                                   status,
                                                   i)
                    continue

                # With multiple hashes in a syntax array we only allow typed
                # hashes.

                # If the data hash only has one field then treat that field as
                # the implicitly typed field.

                if len(item) == 1:
                    if (hash_state & Verifier.__SINGLE_FIELD_HASHES) \
                       and self.__take_single_field_hashes_path(data,
                                                                syntax,
                                                                path,
                                                                status,
                                                                i):
                        continue
                    status.append('Unexpected single type field record with a '
                                  + f"type name of `{item[0].keys()}' found at "
                                  + f"{path}->[{i}].\n")

                # We have multiple fields in the data hash so one of them must
                # be explicitly typed with `t:'.

                else:
                    if (hash_state & Verifier.__TYPED_FIELD_HASHES) \
                       and self.__take_typed_hashes_path(data,
                                                         syntax,
                                                         path,
                                                         status,
                                                         i):
                        continue
                    status.append('Unexpected multi-field record that is '
                                  + 'either untyped or an unrecognised type '
                                  + f'found at {path}->[{i}].\n')

            # We have something other than a scalar, array or hash. This isn't
            # supported.

            else:
                status.append(f"Unsupported data type `{type(item)}' found at "
                              + f'{path}->[{i}].\n')

        # Unlikely but just check for empty arrays.

        if not data and not re.search(syntax[0],
                                      r'^l:choice_(?:list|value)'
                                      + r'(?:,allow_empty_list)?$'):
            status.append(f'Empty list found at {path}. This is not allowed.\n')

    @staticmethod
    def __logger(msg: str):
        print(msg, file = sys.stderr)


def main():
    ret = Verifier.amount_to_units('100')
    print(ret)
    ret = Verifier.amount_to_units('100MB')
    print(ret)
    ret = Verifier.amount_to_units('100MiB')
    print(ret)

    ret = Verifier.duration_to_seconds('500m')
    print(ret)

    #ver = Verifier()
    from pprint import pprint
    Verifier.register_syntax_regex('GLOBAL', '^a-zA-Z$')
    pprint(Verifier.__dict__)

    ver = Verifier()
    ver.register_syntax_regex('mine', '^a-zA-Z$')
    pprint(ver.__dict__)
    ver = Verifier()
    ver.register_syntax_regex('mine', '^a-z[A-Z$')
    pprint(ver.__dict__)


if __name__ == '__main__':
    try:
        main()
    except BaseException as be:
        print(f'Exception: {be}')






## ***** FUNCTIONAL PROTOTYPES *****
#
## Private routines.
#
#state sub check_hashes_in_array;
#state sub check_syntax_tree;
#state sub generate_regexes;
#state sub logger($format, @args)
#{
#    STDERR->printf($format . "\n", @args);
#    return;
#}
#state sub match_syntax;
#state sub take_single_field_hashes_path;
#state sub take_singular_hash_path;
#state sub take_typed_hashes_path;
#state sub throw($format, @args)
#{
#    package Config::Verifier::Exception;
#    use Carp;
#    use overload q("")    => sub { return $_[0]->{msg}; },
#                 bool     => sub { return $_[0]->{msg} ne ''; },
#                 fallback => 1;
#    croak(bless({msg => sprintf($format, @args)}));
#}
#state sub verify_arrays;
#state sub verify_hashes;
#state sub verify_node;
#
## Constructor and destructor.
#
#sub new;
#sub DESTROY;
#
## Public instance methods.
#
#sub check($self, $data, $name)
#{
#    my $this = $Class_Objects{$self->{+__PACKAGE__}};
#    my $status = '';
#    verify_node($this, $data, $this->{syntax_tree}, $name, \$status);
#    return $status;
#}
#sub match_syntax_value($self, $syntax, $value, $error_text = undef)
#{
#    my $this = $Class_Objects{$self->{+__PACKAGE__}};
#    return match_syntax($this, $syntax, $value, $error_text);
#}
#sub syntax_tree($self, $syntax_tree)
#{
#    my $this = $Class_Objects{$self->{+__PACKAGE__}};
#    check_syntax_tree($this, $syntax_tree);
#    $this->{syntax_tree} = $syntax_tree;
#    return;
#}
#
## Public instance and class methods.
#
#sub debug($self, $value = undef)
#{
#    my $old_value;
#    my $this =
#        (ref($self) ne '') ? $Class_Objects{$self->{+__PACKAGE__}} : undef;
#    if (defined($this))
#    {
#        $old_value = $this->{debug};
#        $this->{debug} = $value if (defined($value));
#    }
#    else
#    {
#        $old_value = $Debug;
#        $Debug = $value if (defined($value));
#    }
#    return $old_value;
#}
#sub register_syntax_regex;
#
## Public class methods.
#
#sub amount_to_units;
#sub duration_to_seconds;
#sub string_to_boolean($, $value)
#{
#    return ($value =~ m/^(?:true|yes|y|on|1)$/i) ? 1 : 0;
#}
#
## ***** PACKAGE INFORMATION *****
#
## We are just a base class with nothing additional to export.
#
#use parent qw(Exporter);
#
#our $VERSION = '1.0';
###############################################################################
##
##   Routine      - verify_node
##
##   Description  - Checks the specified structure making sure that the domain
##                  specific syntax is ok.
##
##   Data         - $this   : The internal private object.
##                  $data   : A reference to the data item within the record
##                            that is to be checked. This is either a reference
##                            to an array or a hash as scalars are leaf nodes
##                            and processed inline.
##                  $syntax : A reference to that part of the syntax tree that
##                            is going to be used to check the data referenced
##                            by $data.
##                  $path   : A string containing the current path through the
##                            record for the current item in $data.
##                  $status : A reference to a string that is to contain a
##                            description of what is wrong. If everything is ok
##                            then this string will be empty.
##
###############################################################################
#
#
#
#sub verify_node($this, $data, $syntax, $path, $status)
#{
#
#    my $data_type = ref($data);
#    my $syntax_type = ref($syntax);
#
#    # Check arrays, these are not only lists but also branch points.
#
#    if ($data_type eq 'ARRAY' and $syntax_type eq 'ARRAY')
#    {
#        verify_arrays($this, $data, $syntax, $path, $status);
#    }
#
#    # Check records.
#
#    elsif ($data_type eq 'HASH' and $syntax_type eq 'HASH')
#    {
#        verify_hashes($this, $data, $syntax, $path, $status);
#    }
#
#    # We have a mismatch.
#
#    elsif ($syntax_type eq 'ARRAY')
#    {
#        $$status .= sprintf("The %s field is not a list.\n", $path);
#    }
#    else
#    {
#        $$status .= sprintf("The %s field is not a record.\n", $path);
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - verify_arrays
##
##   Description  - Checks the specified structure making sure that the domain
##                  specific syntax is ok.
##
##   Data         - $this   : The internal private object.
##                  $data   : A reference to the array data item within the
##                            record that is to be checked.
##                  $syntax : A reference to that part of the syntax tree that
##                            is going to be used to check the data referenced
##                            by $data.
##                  $path   : A string containing the current path through the
##                            record for the current item in $data.
##                  $status : A reference to a string that is to contain a
##                            description of what is wrong. If everything is ok
##                            then this string will be empty.
##
###############################################################################
#
#
#
#sub verify_arrays($this, $data, $syntax, $path, $status)
#{
#
#    my $hash_state;
#
#    # Scan through the array looking for a match based upon scalar values and
#    # container types.
#
#    array_element: foreach my $i (0 .. $#$data)
#    {
#
#        my $data_type = ref($data->[$i]);
#
#        # We are comparing scalar values.
#
#        if ($data_type eq '')
#        {
#            my @errs;
#            foreach my $syn_el (@$syntax)
#            {
#                if (ref($syn_el) eq '')
#                {
#                    logger('Comparing `%s->[%u]:%s\' against `%s\'.',
#                           $path,
#                           $i,
#                           $data->[$i],
#                           $syn_el)
#                        if ($this->{debug});
#                    my $err = '';
#                    if (match_syntax($this, $syn_el, $data->[$i], \$err))
#                    {
#                        next array_element;
#                    }
#                    elsif ($err ne '')
#                    {
#                        push(@errs, $err);
#                    }
#                }
#            }
#            $$status .= sprintf('Unexpected %s found at %s->[%u]. It either '
#                                    . 'doesn\'t match the expected value '
#                                    . 'format%s, or a list or record was '
#                                    . "expected instead.\n",
#                                defined($data->[$i])
#                                    ? 'value `' . $data->[$i] . '\''
#                                    : 'undefined value',
#                                $path,
#                                $i,
#                                (@errs) ? ' (' . join(' or ', @errs) . ')'
#                                        : '');
#        }
#
#        # We are comparing arrays.
#
#        elsif ($data_type eq 'ARRAY')
#        {
#
#            my $local_status = '';
#
#            # As we are going off piste into the unknown (arrays don't really
#            # give us much clue as to what we are looking at nor where
#            # decisively to go), we may need to backtrack, so use a local status
#            # string and then only report anything wrong if we don't find a
#            # match at all.
#
#            foreach my $j (0 .. $#$syntax)
#            {
#                if (ref($syntax->[$j]) eq 'ARRAY')
#                {
#                    logger('Comparing `%s->[%u]:(ARRAY)\' against `(ARRAY)\'.',
#                           $path,
#                           $i)
#                        if ($this->{debug});
#                    $local_status = '';
#                    verify_node($this,
#                                $data->[$i],
#                                $syntax->[$j],
#                                $path . '->[' . $i . ']',
#                                \$local_status);
#                    next array_element if ($local_status eq '');
#                }
#            }
#
#            # Only report an error once for each route taken through the syntax
#            # tree.
#
#            if ($local_status eq '')
#            {
#                $$status .= sprintf("Unexpected list found at %s->[%u].\n",
#                                    $path,
#                                    $i);
#            }
#            else
#            {
#                $$status .= $local_status;
#            }
#
#        }
#
#        # We are comparing hashes, records, so look to see if there is a common
#        # field in one of the syntax hashes. If so then take that branch.
#
#        elsif ($data_type eq 'HASH')
#        {
#
#            # If we haven't done it already, determine what type of hashes we
#            # have in the syntax array (just one or multiple that are typed in
#            # some way).
#
#            $hash_state = check_hashes_in_array($syntax)
#                unless (defined($hash_state));
#
#            # If there is one hash in the syntax array then that's our path.
#
#            if ($hash_state == ONE_HASH)
#            {
#                take_singular_hash_path($this,
#                                        $data,
#                                        $syntax,
#                                        $path,
#                                        $status,
#                                        $i);
#                next array_element;
#            }
#
#            # With multiple hashes in a syntax array we only allow typed hashes.
#
#            # If the data hash only has one field then treat that field as the
#            # implicitly typed field.
#
#            if (keys(%{$data->[$i]}) == 1)
#            {
#                if (($hash_state & SINGLE_FIELD_HASHES)
#                    and take_single_field_hashes_path($this,
#                                                      $data,
#                                                      $syntax,
#                                                      $path,
#                                                      $status,
#                                                      $i))
#                {
#                    next array_element;
#                }
#                $$status .= sprintf('Unexpected single type field record with '
#                                        . 'a type name of `%s\' found at '
#                                        . "%s->[%u].\n",
#                            (keys(%{$data->[$i]}))[0],
#                            $path,
#                            $i);
#            }
#
#            # We have multiple fields in the data hash so one of them must be
#            # explicitly typed with `t:'.
#
#            else
#            {
#                if (($hash_state & TYPED_FIELD_HASHES)
#                    and take_typed_hashes_path($this,
#                                               $data,
#                                               $syntax,
#                                               $path,
#                                               $status,
#                                               $i))
#                {
#                    next array_element;
#                }
#                $$status .= sprintf('Unexpected multi-field record that is '
#                                        . 'either untyped or an unrecognised '
#                                        . "type found at %s->[%u].\n",
#                                    $path,
#                                    $i);
#            }
#
#        }
#
#        # We have something other than a scalar, array or hash. This isn't
#        # supported.
#
#        else
#        {
#            $$status .= sprintf('Unsupported data type `%s\' found at '
#                                    . "%s->[%u].\n",
#                                $data_type,
#                                $path,
#                                $i);
#        }
#
#    }
#
#    # Unlikely but just check for empty arrays.
#
#    if (@$data == 0 and $syntax->[0]
#        !~ m/^l:choice_(?:list|value)(?:,allow_empty_list)?$/)
#    {
#        $$status .= sprintf("Empty list found at %s. This is not allowed.\n",
#                            $path);
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - verify_hashes
##
##   Description  - Checks the specified structure making sure that the domain
##                  specific syntax is ok.
##
##   Data         - $this   : The internal private object.
##                  $data   : A reference to the hash data item within the
##                            record that is to be checked.
##                  $syntax : A reference to that part of the syntax tree that
##                            is going to be used to check the data referenced
##                            by $data.
##                  $path   : A string containing the current path through the
##                            record for the current item in $data.
##                  $status : A reference to a string that is to contain a
##                            description of what is wrong. If everything is ok
##                            then this string will be empty.
##
###############################################################################
#
#
#
#sub verify_hashes($this, $data, $syntax, $path, $status)
#{
#
#    # Check that all mandatory fields are present.
#
#    foreach my $key (keys(%$syntax))
#    {
#        if ($key =~ m/^[mt]\:(.+)$/)
#        {
#            my $mandatory_field = $1;
#            if (not exists($data->{$mandatory_field}))
#            {
#                $$status .= sprintf('The %s record does not contain the '
#                                        . "mandatory field `%s'.\n",
#                                    $path,
#                                    $mandatory_field);
#            }
#        }
#    }
#
#    # Check each field.
#
#    hash_key: foreach my $field (keys(%$data))
#    {
#
#        my $syn_el;
#
#        # Locate the matching field in the syntax tree.
#
#        foreach my $type ('m:', 's:', 't:')
#        {
#            if (exists($syntax->{$type . $field}))
#            {
#                $syn_el = $syntax->{$type . $field};
#                last;
#            }
#        }
#        if (not defined($syn_el))
#        {
#            foreach my $key (keys(%$syntax))
#            {
#                if (match_syntax($this, $key, $field))
#                {
#                    $syn_el = $syntax->{$key};
#                    last;
#                }
#            }
#        }
#
#        # Deal with unknown fields, which are ok if we have custom fields in the
#        # record.
#
#        if (not defined($syn_el))
#        {
#            $$status .= sprintf('The %s record contains an invalid field '
#                                    . "`%s'.\n",
#                                $path,
#                                $field);
#            next hash_key;
#        }
#
#        # Skip custom fields.
#
#        next hash_key if ($syn_el eq 'c:');
#
#        # Ok now check that the value is correct and process it.
#
#        my $syntax_type = ref($syn_el);
#        my $field_type = ref($data->{$field});
#
#        logger('Comparing `%s->%s:%s\' against `%s\'.',
#               $path,
#               $field,
#               ($field_type eq '') ? $data->{$field} : '(' . $field_type . ')',
#               ($syntax_type eq '') ? $syn_el : '(' . $syntax_type . ')')
#            if ($this->{debug});
#
#        # Scalar - scalar.
#
#        if ($syntax_type eq '' and $field_type eq '')
#        {
#            my $err = '';
#            if (not match_syntax($this, $syn_el, $data->{$field}, \$err))
#            {
#                $$status .= sprintf('Unexpected %s found at %s. It doesn\'t '
#                                        . 'match the expected value '
#                                        . "format%s.\n",
#                                    defined($data->{$field})
#                                        ? 'value `' . $data->{$field} . '\''
#                                        : 'undefined value',
#                                    $path . '->' . $field,
#                                    ($err ne '') ? " ($err)" : '');
#            }
#        }
#
#        # List of choice values, i.e. a single field that can match against one
#        # of the values in the list (which may include arrays and hashes as well
#        # as scalars).
#
#        elsif ($syntax_type eq 'ARRAY' and $syn_el->[0] =~ m/^l:choice_value/)
#        {
#
#            # This is done simply by faking an array with the one entry being
#            # the data item and then handling it as a standard array. We then
#            # alter any returned message to remove this fake array from the
#            # path.
#
#            my $local_status = '';
#            my $new_path = $path . '->' . $field;
#            verify_arrays($this,
#                          [$data->{$field}],
#                          $syn_el,
#                          $new_path,
#                          \$local_status);
#            if ($local_status ne '')
#            {
#                $local_status =~
#                    s/^(.+? \Q${new_path}\E)->\[0\](.*)$/${1}${2}/s;
#                $$status .= $local_status;
#            }
#
#        }
#
#        # Array - array or hash - hash.
#
#        elsif (($syntax_type eq 'ARRAY' or $syntax_type eq 'HASH')
#               and $syntax_type eq $field_type)
#        {
#            verify_node($this,
#                        $data->{$field},
#                        $syn_el,
#                        $path . '->' . $field,
#                        $status);
#        }
#
#        # Assorted mismatches.
#
#        elsif ($syntax_type eq '')
#        {
#            $$status .= sprintf('The %s field does not contain a simple '
#                                    . "value.\n",
#                                $path . '->' . $field);
#        }
#        elsif ($syntax_type eq 'ARRAY')
#        {
#            $$status .= sprintf("The %s field is not a list.\n",
#                                $path . '->' . $field);
#        }
#        else
#        {
#            $$status .= sprintf("The %s field is not a record.\n",
#                                $path . '->' . $field);
#        }
#
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - check_hashes_in_array
##
##   Description  - Checks the specified syntax array checking that the hashes
##                  must be typed in some way if more than one hash is present.
##
##   Data         - $syntax      : A reference to that part of the syntax tree
##                                 that is going to be checked.
##                  Return Value : A bit mask with bits set according to what
##                                 was found.
##
###############################################################################
#
#
#
#sub check_hashes_in_array($syntax)
#{
#
#    my $nr_hashes = 0;
#    my $single_typed_field_hashes;
#    my $typed_field_hashes;
#    my $untyped_field_hashes;
#
#    foreach my $syn_el (@$syntax)
#    {
#        if (ref($syn_el) eq 'HASH')
#        {
#            ++ $nr_hashes;
#            if (keys(%$syn_el) == 1)
#            {
#                $single_typed_field_hashes = 1;
#
#                # Custom fields can't be matched against as they are undefined.
#
#                throw('%s(record type fields cannot be of type `c:\').',
#                      SCHEMA_ERROR)
#                    if ((keys(%$syn_el))[0] eq 'c:');
#            }
#            else
#            {
#                my $nr_typed_keys = 0;
#                my $typed;
#                foreach my $syn_key (keys(%$syn_el))
#                {
#                    if ($syn_key =~ m/^t:/)
#                    {
#                        $typed = 1;
#                        $typed_field_hashes = 1;
#                        ++ $nr_typed_keys;
#                        throw('%s(only one typed field can be present in a '
#                                  . 'record).',
#                              SCHEMA_ERROR)
#                            if ($nr_typed_keys > 1);
#                    }
#                }
#                $untyped_field_hashes = 1 unless ($typed);
#            }
#        }
#    }
#
#    if ($nr_hashes == 1)
#    {
#        return ONE_HASH;
#    }
#    throw('%s(untyped records must be the only record in a list).',
#          SCHEMA_ERROR)
#        if ($untyped_field_hashes);
#    my $state = 0;
#    $state |= SINGLE_FIELD_HASHES if ($single_typed_field_hashes);
#    $state |= TYPED_FIELD_HASHES if ($typed_field_hashes);
#
#    return $state;
#
#}
##
###############################################################################
##
##   Routine      - take_singular_hash_path
##
##   Description  - Checks the specified syntax array looking for a singular
##                  hash and then takes that path.
##
##   Data         - $this   : The internal private object.
##                  $data   : A reference to the array data item within the
##                            record that is to be checked.
##                  $syntax : A reference to that part of the syntax tree that
##                            is going to be used to check the data referenced
##                            by $data.
##                  $path   : A string containing the current path through the
##                            record for the current item in $data.
##                  $status : A reference to a string that is to contain a
##                            description of what is wrong. If everything is ok
##                            then this string will be empty.
##                  $i      : The current index in the data array.
##
###############################################################################
#
#
#
#sub take_singular_hash_path($this, $data, $syntax, $path, $status, $i)
#{
#
#    foreach my $syn_el (@$syntax)
#    {
#        if (ref($syn_el) eq 'HASH')
#        {
#            logger('Comparing `%s->[%u]:%s\' against `%s\'.',
#                   $path,
#                   $i,
#                   join('|', keys(%{$data->[$i]})),
#                   join('|', keys(%$syn_el)))
#                if ($this->{debug});
#            verify_node($this,
#                        $data->[$i],
#                        $syn_el,
#                        $path . '->[' . $i . ']',
#                        $status);
#            return;
#        }
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - take_typed_hashes_path
##
##   Description  - Checks the specified syntax array checking for only hashes
##                  that contain special typed fields and then takes the path
##                  of a matching hash.
##
##   Data         - $this        : The internal private object.
##                  $data        : A reference to the array data item within
##                                 the record that is to be checked.
##                  $syntax      : A reference to that part of the syntax tree
##                                 that is going to be used to check the data
##                                 referenced by $data.
##                  $path        : A string containing the current path through
##                                 the record for the current item in $data.
##                  $status      : A reference to a string that is to contain a
##                                 description of what is wrong. If everything
##                                 is ok then this string will be empty.
##                  $i           : The current index in the data array.
##                  Return Value : True if a path was taken, otherwise false if
##                                 not.
##
###############################################################################
#
#
#
#sub take_typed_hashes_path($this, $data, $syntax, $path, $status, $i)
#{
#
#    # Look for a special matching type field and value. This will give an exact
#    # match if set up correctly.
#
#    foreach my $data_key (keys(%{$data->[$i]}))
#    {
#        my $syn_key = 't:' . $data_key;
#        foreach my $syn_el (@$syntax)
#        {
#            if (ref($syn_el) eq 'HASH'
#                and exists($syn_el->{'t:' . $data_key})
#                and match_syntax($this,
#                                 $syn_el->{'t:' . $data_key},
#                                 $data->[$i]->{$data_key}))
#            {
#                logger('Comparing `%s->[%u]:%s\' against `%s\' based on type '
#                           . 'field `%s\'.',
#                       $path,
#                       $i,
#                       join('|', keys(%{$data->[$i]})),
#                       join('|', keys(%$syn_el)),
#                       $data_key)
#                    if ($this->{debug});
#                verify_node($this,
#                            $data->[$i],
#                            $syn_el,
#                            $path . '->[' . $i . ']',
#                            $status);
#                return 1;
#            }
#        }
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - take_single_field_hashes_path
##
##   Description -  Checks the specified syntax array checking for hashes that
##                  contain only one field and then takes the path of a
##                  matching hash.
##
##   Data         - $this        : The internal private object.
##                  $data        : A reference to the array data item within
##                                 the record that is to be checked.
##                  $syntax      : A reference to that part of the syntax tree
##                                 that is going to be used to check the data
##                                 referenced by $data.
##                  $path        : A string containing the current path through
##                                 the record for the current item in $data.
##                  $status      : A reference to a string that is to contain a
##                                 description of what is wrong. If everything
##                                 is ok then this string will be empty.
##                  $i           : The current index in the data array.
##                  Return Value : True if a path was taken, otherwise false if
##                                 not.
##
###############################################################################
#
#
#
#sub take_single_field_hashes_path($this, $data, $syntax, $path, $status, $i)
#{
#
#    my $data_key = (keys(%{$data->[$i]}))[0];
#    foreach my $syn_el (@$syntax)
#    {
#        if (ref($syn_el) eq 'HASH' and keys(%$syn_el) == 1)
#        {
#            my $syn_key = (keys(%$syn_el))[0];
#            if (match_syntax($this, $syn_key, $data_key))
#            {
#                logger('Comparing `%s->[%u]:%s\' against `%s\'.',
#                       $path,
#                       $i,
#                       $data_key,
#                       $syn_key)
#                    if ($this->{debug});
#                verify_node($this,
#                            $data->[$i],
#                            $syn_el,
#                            $path . '->[' . $i . ']',
#                            $status);
#                return 1;
#            }
#
#        }
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   Routine      - match_syntax
##
##   Description  - Tests a value against an item in the syntax tree.
##
##   Data         - $this        : The internal private object.
##                  $syntax      : The element in the syntax tree that the
##                                 value is to be compared against.
##                  $value       : The string that is to be compared against
##                                 the syntax element. This is not given when
##                                 checking the syntax tree for errors.
##                  $error_text  : A reference to the string that is to contain
##                                 expected type or range mismatch information.
##                                 This is optional.
##                  Return Value : True for a match, otherwise false.
##
###############################################################################
#
#
#
#sub match_syntax($this, $syntax, $value = {}, $error_text = undef)
#{
#
#    my ($arg,
#        $result,
#        $type);
#
#    # We don't allow undefined values and so never match.
#
#    return unless(defined($value));
#
#    # If $value hasn't been specified then reset it to undef.
#
#    $value = undef if (ref($value) eq 'HASH');
#
#    # It's an error if a syntax entry is undefined.
#
#    throw('%s(syntax = `undef\').', SCHEMA_ERROR) unless (defined($syntax));
#
#    # Decide what to do based upon the header.
#
#    if ($syntax =~ m/^([cfilmRrst]):(.*)/)
#    {
#        $type = $1;
#        $arg = $2;
#    }
#    else
#    {
#        throw('%s(syntax = `%s\').', SCHEMA_ERROR, $syntax);
#    }
#    if ($type eq 'c')
#    {
#        throw('%s(syntax = `%s\', custom field entries have no name).',
#              SCHEMA_ERROR,
#              $syntax)
#            if ($arg ne '');
#        $result = 1;
#    }
#    elsif ($type eq 'f')
#    {
#        my $float_re = '[-+]?(?=\d|\.\d)\d*(?:\.\d*)?(?:[Ee][-+]?\d+)?';
#        if ($arg =~ m/^(?:($float_re))?(?:,($float_re))?$/)
#        {
#            my ($min, $max) = ($1, $2);
#            throw('%s(syntax = `%s\', minimum is greater than maximum).',
#                  SCHEMA_ERROR,
#                  $syntax)
#                if (defined($min) and defined($max) and $min  > $max);
#            if (defined($value)
#                and $value =~ m/^$float_re$/
#                and (not defined($min) or $value >= $min)
#                and (not defined($max) or $value <= $max))
#            {
#                $result = 1;
#            }
#            elsif (defined($error_text))
#            {
#                $$error_text =
#                    sprintf('float between %s and %s',
#                            defined($min) ? $min : '<No Lower Limit>',
#                            defined($max) ? $max : '<No Upper Limit>');
#            }
#        }
#        else
#        {
#            throw('%s(syntax = `%s\').', SCHEMA_ERROR, $syntax);
#        }
#    }
#    elsif ($type eq 'i')
#    {
#        my $int_re = '[-+]?\d+';
#        if ($arg =~ m/^(?:($int_re))?(?:,($int_re)?)?(?:,($int_re)?)?$/)
#        {
#            my ($min, $max, $step) = ($1, $2, $3);
#            throw('%s(syntax = `%s\', minimum is greater than maximum).',
#                  SCHEMA_ERROR,
#                  $syntax)
#                if (defined($min) and defined($max) and $min  > $max);
#            throw('%s(syntax = `%s\', minimum/maximum values are not '
#                      . 'compatible with step value).',
#                  SCHEMA_ERROR,
#                  $syntax)
#                if (defined($step)
#                    and ((defined($min) and ($min % $step) != 0)
#                         or (defined($max) and ($max % $step) != 0)));
#            if (defined($value)
#                and $value =~ m/^$int_re$/
#                and (not defined($min) or $value >= $min)
#                and (not defined($max) or $value <= $max)
#                and (not defined($step) or ($value % $step) == 0))
#            {
#                $result = 1;
#            }
#            elsif (defined($error_text))
#            {
#                $$error_text =
#                    sprintf('integer between %s and %s%s',
#                            defined($min) ? $min : '<No Lower Limit>',
#                            defined($max) ? $max : '<No Upper Limit>',
#                            defined($step) ? " with a step size of $step" : '');
#            }
#        }
#        else
#        {
#            throw('%s(syntax = `%s\').', SCHEMA_ERROR, $syntax);
#        }
#    }
#    elsif ($type eq 'l')
#    {
#
#        # List types are special in that they are ignored when matching data
#        # values, but they determine the way arrays of entries are handled. So
#        # we only check the validity of their setting.
#
#        throw('%s(syntax = `%s\', type of list is must be `choice_list\' or '
#                  . '`choice_value\' optionally followed by '
#                  . '`,allow_empty_list\').',
#              SCHEMA_ERROR,
#              $syntax)
#            if ($arg !~ m/^choice_(?:list|value)(?:,allow_empty_list)?$/);
#
#    }
#    elsif ($type eq 'R')
#    {
#        if (exists($this->{syntax_regexes}->{$arg}))
#        {
#            $result = 1
#                if (defined($value)
#                    and $value =~ m/$this->{syntax_regexes}->{$arg}/);
#        }
#        else
#        {
#            throw('%s(syntax = `%s\', unknown syntactic regular expression).',
#                  SCHEMA_ERROR,
#                  $syntax);
#        }
#    }
#    elsif ($type eq 'r')
#    {
#        throw('`%s\' is not anchored to the start and end of the string.',
#              $arg)
#            if ($arg !~ m/^\^.*\$$/);
#        local $@;
#        eval
#        {
#            if (defined($value))
#            {
#                $result = 1 if ($value =~ m/$arg/);
#            }
#            else
#            {
#                my $dummy = qr/$arg/;
#            }
#            1;
#        }
#        or do
#        {
#            my $err = $@;
#            $err =~ s/ at .+ line \d+\..*//gs;
#            throw($err);
#        };
#    }
#    else
#    {
#        $result = 1 if (defined($value) and $arg eq $value);
#    }
#
#    logger('Comparing `%s\' against `%s\'. Match: %s.',
#           $syntax,
#           $value,
#           ($result) ? 'Yes' : 'No')
#        if ($this->{debug} and defined($value));
#
#    return $result;
#
#}
##
###############################################################################
##
##   Routine      - generate_regexes
##
##   Description  - Generate the less simple regular expressions. This code is
##                  very closely based on the _init_regexp() routine from
##                  Lionel Cons's Config::Validator module.
##
##   Data         - None.
##
###############################################################################
#
#
#
#sub generate_regexes()
#{
#
#    # The parentheses below are meant to be non-capturing however with all the
#    # colons scattered around it's less confusing to use `(...)' rather than
#    # `(?:...)'. This is then patched up afterwards.
#
#    my $label = '[[:alnum:]]([[:alnum:]-]{0,61}[[:alnum:]])?';
#    my $byte = '25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d';
#    my $cidr4 = '(3[0-2]|[1-2]?\d)';
#    my $cidr6 = '(12[0-8]|1[0-1]\d|[1-9]?\d)';
#    my $hex4 = '[0-9a-fA-F]{1,4}';
#    my $ipv4 = "(($byte)\\.){3}($byte)";
#    my @tail = (':',
#                "(:($hex4)?|($ipv4))",
#                ":(($ipv4)|$hex4(:$hex4)?|)",
#                "(:($ipv4)|:$hex4(:($ipv4)|(:$hex4){0,2})|:)",
#                "((:$hex4){0,2}(:($ipv4)|(:$hex4){1,2})|:)",
#                "((:$hex4){0,3}(:($ipv4)|(:$hex4){1,2})|:)",
#                "((:$hex4){0,4}(:($ipv4)|(:$hex4){1,2})|:)");
#    my $ipv6 = $hex4;
#    foreach my $tail (@tail)
#    {
#        $ipv6 = "$hex4:($ipv6|$tail)";
#    }
#    $ipv6 = "(:(:$hex4){0,5}((:$hex4){1,2}|:$ipv4)|$ipv6)";
#
#    # The look ahead for hostname ensures that there's a letter somewhere in the
#    # host name.
#
#    my $hostname = "(?=.*[[:alpha:]])($label\\.)*$label";
#
#    # Make non-capturing, compile and then store the regexes in the main syntax
#    # table.
#
#    my %regexes =
#        (hostname     => $hostname,
#         ipv4_addr    => $ipv4,
#         ipv4_cidr    => "$ipv4/$cidr4",
#         ipv6_addr    => $ipv6,
#         ipv6_cidr    => "$ipv6/$cidr6",
#         windows_path => "(\\\\\\\\$hostname\\\\|[[:alpha:]]:(\\\\)?)?"
#                             . '((?=.*[^\\\\])(?!.*[<>:"/|?*]).)+');
#    foreach my $name (keys(%regexes))
#    {
#        $regexes{$name} =~ s/\((?!\?)/(?:/g;
#        $Syntax_Regexes{$name} = qr/^(?:$regexes{$name})$/;
#    }
#
#    # Now compile up the capturing regex strings into capturing and
#    # non-capturing objects.
#
#    for my $name (keys(%Capturing_Regexes))
#    {
#        my $non_capturing = ($Capturing_Regexes{$name} =~ s/\((?!\?)/(?:/gr);
#        $Syntax_Regexes{$name} = qr/$non_capturing/;
#        $Capturing_Regexes{$name} = qr/$Capturing_Regexes{$name}/;
#    }
#
#    return;
#
#}
##
###############################################################################
##
##   On Load Initialisation Code
##
###############################################################################
#
#
#
#generate_regexes();
#1;
##
###############################################################################
##
##   Documentation
##
###############################################################################
#
#
#
#__END__
#
#=pod
#
#=head1 NAME
#
#Config::Verifier - Verify the structure and values inside Perl data structures
#
#=head1 VERSION
#
#1.0
#
#=head1 SYNOPSIS
#
#  use Config::Verifier;
#  my %settings_syntax_tree =
#      ('m:config_version' => SYNTAX_FLOAT,
#       's:service'        =>
#           {'s:log_level'               => 'r:^(?i:ERROR'
#                                               . '|WARNING'
#                                               . '|ADVISORY'
#                                               . '|INFORMATION'
#                                               . '|AUTHENTICATION'
#                                               . '|DEBUG)$',
#            's:debug_options'           => ['r:^(?i:DEBUG_EVERYTHING'
#                                            . '|DEBUG_AUTHENTICATION'
#                                            . '|DEBUG_RAW_SETTINGS_DUMP'
#                                            . '|DEBUG_SETTINGS_DUMP'
#                                            . '|DEBUG_SYSTEM_USERS_DUMP'
#                                            . '|DEBUG_STACK_TRACES)$'],
#            's:hostname_cache'          =>
#                {'s:ttl'            => 'R:duration',
#                 's:purge_interval' => 'R:duration'},
#            's:lowercase_usernames'     => 'R:boolean',
#            's:plugins_directory'       => 'R:path',
#            's:system_users_cache_file' => 'R:path',
#            's:use_syslog'              => 'R:boolean'},
#       's:allowed_hosts'  =>
#           ['R:hostname',
#            'R:ipv4_addr',
#            'R:ipv4_cidr',
#            'R:ipv6_addr',
#            'R:ipv6_cidr'],
#       's:denied_hosts'  =>
#           ['R:hostname',
#            'R:ipv4_addr',
#            'R:ipv4_cidr',
#            'R:ipv6_addr',
#            'R:ipv6_cidr']);
#  my $data = YAML::XS::LoadFile('my-config.yml');
#  my $verifier = Config::Verifier->new(\%settings_syntax_tree);
#  my $status = $verifier->check($data);
#  die("Syntax error detected. The reason given was:\n" . $status)
#      if ($status ne '');
#
#=head1 DESCRIPTION
#
#The Config::Verifier class checks the given Perl data structure against the
#specified syntax tree. Whilst it can be used to verify any structured data
#ingested into Perl, its main purpose is to check human generated configuration
#data as the error messages are designed to be informative and helpful. It's also
#designed to be lightweight, not having any dependencies beyond the core Perl
#modules.
#
#When reading in configuration data from a file, it's up to the caller to decide
#exactly how this is done. Typically one would use some sort of parsing module
#like L<JSON> or L<YAML::XS> (which I have found to be the more stringent for
#YAML files).
#
#Whilst this module could be used to verify data from many sources, like RESTful
#API requests, you would invariably be better off with a module that could read
#in a proper schema in an officially recognised format. One such module, for
#validating both JSON and YAML is L<JSON::Validator>. However due to its very
#capable nature, it does pull in a lot of dependencies, which can be undesirable
#for smaller projects, hence this module.
#
#If this module is not to your liking then another option, which I believe
#supports ini style configuration files, is L<Config::Validator>.
#
#=head1 CONSTRUCTOR
#
#=over 4
#
#=item B<new([$syntax_tree])>
#
#Creates a new Config::Verifier object. C<$syntax_tree> is an optional reference
#to a syntax tree that describes what data should be present and its basic
#format.
#
#=back
#
#=head1 SUBROUTINES/METHODS
#
#=over 4
#
#=item B<amount_to_units($amount)[, $want_bits]>
#
#Converts the amount given in C<$amount> into units. An amount takes the form as
#described by C<'R:amount'> or C<'R:amount_data'> and is either a number
#optionally followed K, M, G, or T, or a number followed by KB, Kb, KiB, Kib up
#to up to TB etc respectively. For the data amounts B and b refer to bytes and
#bits, whilst KiB and KB refer to 1024 bytes and 1000 bytes and so on. If
#C<$want_bits> is set to true then the returned amount is in bits rather than
#bytes. The default default is false and it only applies to amounts of data.
#
#=item B<check($data, $name)>
#
#Checks the specified structure making sure that the domain specific syntax is
#ok.
#
#C<$data> is a reference to the data structure that is to be checked, typically a
#hash, i.e. a record, but it can also be a list. C<$name> is a string containing
#a descriptive name for the data structure being checked. This will be used as
#the base name in any error messages returned by this method.
#
#=item B<debug([$flag])>
#
#Turns on the output of debug messages to C<STDERR> when C<$flag> is set to true,
#otherwise debug messages are turned off. If C<$flag> isn't specified then
#nothing changes.
#
#The any new debug setting is either changed globally, which will affect all
#newly created objects, or just changed within the current object, depending upon
#whether this method is called as a class or an instance method.
#
#=item B<duration_to_seconds($duration)>
#
#As above but for seconds. A duration takes the form as described by
#C<'R:duration_seconds'> and is a number followed by a time unit that can be one
#of s, m, h, d, or w for seconds, minutes, hours, days and weeks respectively.
#
#=item B<match_syntax_value($syntax, $value[, $error])>
#
#Tests the data in C<$value> against a syntax pattern as given by C<$syntax>. A
#syntax pattern is something like C<'R:hostname'> or C<'i:1,10'>. C<$error> is an
#optional reference to a string that is to contain any type/value errors that are
#detected.
#
#=item B<register_syntax_regex($name, $regex)>
#
#Registers the regular expression string C<$regex>, which is not a compiled RE
#object, as a syntax pattern under the name given in C<$name>. This is then
#available for use as C<'R:name'> just like the built in syntax patterns. This
#can be used to replace most built in patterns or extend the list of patterns.
#The regular expression must be anchored, i.e. start and end with C<^> and C<$>
#respectively.
#
#The new regular expression term either goes into the global default table, which
#will affect newly created objects, or the object's own private table, depending
#upon whether this method is called as a class or an instance method.
#
#=item B<string_to_boolean($string)>
#
#Converts the amount given in C<$string> into a boolean (1 or 0). A string
#representing a boolean takes the form as described by C<'R:boolean'> and can be
#one of true, yes, Y, y, or on for true and false, no N, n, off or '' for false.
#
#=item B<syntax_tree($syntax_tree)>
#
#Sets the object's syntax tree reference to the one given in C<$syntax_tree>.
#
#=back
#
#=head1 RETURN VALUES
#
#C<new()> returns a new Config::Verifier object.
#
#C<amount_to_units()> returns an integer.
#
#C<check()> returns a string containing the details of the problems encountered
#when parsing the data on failure, otherwise an empty string on success.
#
#C<debug()> returns the previous debug message setting as a boolean.
#
#C<duration_to_seconds()> returns the number of seconds that the specified
#duration represents.
#
#C<match_syntax_value()> returns true for a match, otherwise false for no match.
#
#C<register_syntax_regex()> returns nothing.
#
#C<string_to_boolean()> returns a boolean.
#
#C<syntax_tree()> returns nothing.
#
#=head1 NOTES
#
#=head2 Syntax Patterns
#
#Syntax patterns are used to match against specific values. These are expressed
#as anchored regular expressions and can be registered, either built in or
#registered by the caller an runtime (denoted by C<'R:'>), or simply provided
#directly in the syntax tree (denoted by C<'r:'>).
#
#The built in registered ones are:
#
#    R:amount
#    R:amount_data
#    R:anything
#    R:boolean
#    R:duration
#    R:hostname
#    R:ipv4_addr
#    R:ipv4_cidr
#    R:ipv6_addr
#    R:ipv6_cidr
#    R:name
#    R:plugin
#    R:printable
#    R:string
#    R:unix_path
#    R:user_name
#    R:variable
#    R:windows_path
#
#One can add to the built in list or replace existing entries by using the
#C<register_syntax_regex()> method.
#
#=head2 Syntax Trees
#
#These trees, a container of some sort, typically a hash, describe what should
#appear in a given data structure. The hash's key names represent fields that can
#be present and their values either refer to further containers, for nested
#records or lists, or strings that describe the type of value that should be
#present for that field. Key names are strings that consist of a type character
#followed by a colon and then the field name. Key and value types are as follows:
#
#    c:      - Custom entries follow, i.e. a key lookup failure isn't an
#              error. This is used to cater for parts of a syntax tree that
#              need to be dynamic and handled separately.
#    f:m,M   - A floating point number with optional minimum and Maximum
#              qualifiers.
#    i:m,M,s - An integer with optional minimum, Maximum and step qualifiers.
#    l:type  - The type of list in the syntax tree. This determines how lists
#              are treated. There are two types choice_list, the default, and
#              choice_value:
#              choice_list:  With this type a list is expected in the data,
#                            with each element of the syntax list
#                            representing one of the allowed types that an
#                            entry can take within the data list.
#              choice_value: With this type a singular item is expected in
#                            the data, with each element of the syntax list
#                            representing one of the allowed types that the
#                            data item can be. Having said that, should a
#                            list or record be specified in the syntax list
#                            then this permits the singular data item to also
#                            be a list or record. Thus you could use this
#                            type of list to have a field that could take a
#                            scalar value, a list or a record.
#              Each type can also take an additional allow_empty_list
#              qualifier (separated by a comma). This permits the list to be
#              empty in the data. The default is to treat an empty list as an
#              error.
#    m:s     - A plain string literal s, representing the name of a mandatory
#              field, which is case sensitive.
#    R:n     - A built in regular expression with the name n, that is used to
#              match against acceptable values. This can also be used to
#              match against optional fields that fit that pattern.
#    r:reg   - Like R:n but the regular expression is supplied by the caller.
#    s:s     - A plain string literal s, representing the the name
#              of an optional field or a literal value, both or which are
#              which are case sensitive.
#    t:s     - Like m: but also signifies a typed field, i.e. a field that
#              uniquely identifies the type of the record via its value. Its
#              corresponding value must uniquely identify the type of record
#              within the list of records at that point in the schema.
#    Lists   - These represent not only that a list of items should be
#              present but also that there can be a choice in the different
#              types of items, e.g scalar, list or hash.
#    Hashes  - These represent records with named fields.
#
#Typically keys can be anything other than containers and values are specific
#types, regular expressions or containers. The R: style syntax patterns mentioned
#above provide regular expressions for the more common syntax elements.
#
#Please see the example under L</SYNOPSIS>.
#
#=head1 DIAGNOSTICS
#
#One can generate lots of tracing messages to C<STDERR> when debug mode is turned
#on via the C<debug()> method.
#
#With the exception of the C<debug()> and C<string_to_boolean()> methods,
#exceptions are thrown when there is a problem with the supplied syntax tree or
#value. Since illegal values read in from configuration data will be detected
#when it is parsed, exceptions from these methods will most likely indicate a
#fault with the calling program. Exceptions from this library are
#C<Config::Verifier::Exception> objects that can be cast to strings.
#
#Problems with the data being parsed are returned as a string from the C<check()>
#method. Where possible all parsing errors will be listed, one line per error, in
#a form suitable for the end user.
#
#=head1 DEPENDENCIES
#
#None beyond the core Perl modules.
#
#=head1 SEE ALSO
#
#L<Config::Validator>,
#L<JSON::Validator>,
#L<JSON>,
#L<YAML::XS>
#
#=head1 BUGS AND LIMITATIONS
#
#Whilst this module could be used to validate data conforming to a schema it's
#really designed for checking configuration data. If used in high data rate
#communications you will probably find other libraries better able to support
#standard schema definitions and possibly in a more performant way.
#
#=head1 AUTHOR
#
#Anthony Edward Cooper. Please report all faults and suggestions to
#<aecooper@cpan.org>.
#
#=head1 LICENSE AND COPYRIGHT
#
#Copyright (C) 2024 by Anthony Cooper <aecooper@cpan.org>.
#
#This library is free software; you can redistribute it and/or modify it under
#the terms of the GNU Lesser General Public License as published by the Free
#Software Foundation; either version 3 of the License, or (at your option) any
#later version.
#
#This library is distributed in the hope that it will be useful, but WITHOUT ANY
#WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
#PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public License along
#with this library; if not, write to the Free Software Foundation, Inc., 59
#Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#
#=cut
#
