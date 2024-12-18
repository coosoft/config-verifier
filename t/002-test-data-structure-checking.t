#!/usr/bin/env perl

use 5.036;
use strict;
use warnings;

use Test::More;

use Config::Verifier;

my $exception = '';
sub exception_protect($fn)
{

    $exception = '';

    local $@;
    my $ret_val;
    eval
    {
        $ret_val = &$fn();
        1;
    }
    or do
    {
        $exception = "$@";
        note("Exception thrown [$exception]");
        return undef;
    };

    return $ret_val;

}

my (%data,
    $status,
    %syntax_tree);
my $verifier = Config::Verifier->new();

# A Good syntax tree.

my @host =
    ('l:choice_value',
     'R:hostname',
     'R:ipv4_addr',
     'R:ipv6_addr');
%syntax_tree =
    ('m:config_version' => 'f:0',
     's:settings'       =>
         {'s:terminal'              => ['R:anything'],
          's:editor'                => ['R:anything'],
          's:tigervnc_profile_path' => 'R:unix_path',
          's:debug'                 => 'R:boolean'},
     'm:menu'           =>
         [{'m:separator' =>
               {'s:text'      => 'R:printable',
                's:draw_line' => 'R:boolean'}},
          {'m:rdp'       =>
               {'m:name'               => 'R:printable',
                'm:host'               => \@host,
                's:port'               => 'i:1,65535',
                's:user'               => 'R:user_name',
                's:domain_name'        => 'R:hostname',
                's:window_mode'        => 'r:^(?:fullscreen'
                                              . '|maximised-no-boarders)'
                                              . '|(?:\d+x\d+)$',
                's:colour_depth'       => 'r:^8|18|24|32$'}},
          {'m:vnc'       =>
               {'m:name'               => 'R:printable',
                'm:host'               => \@host,
                's:port'               => 'i:1,65535',
                's:profile'            => 'r:^[^/]+$'}},
          {'m:ssh'       =>
               {'m:name'               => 'R:printable',
                'm:host'               => \@host,
                's:port'               => 'i:1,65535',
                's:user'               => 'R:user_name'}}]);
$verifier->syntax_tree(\%syntax_tree);

# Good syntax tree and data.

%data =
    (config_version => 1.0,
     menu           => [{vnc => {name => 'Desktop',
                                 host => 'desktop.acme.co.uk',
                                 port => 5901}},
                        {rdp => {name        => 'Windows 11',
                                 host        => 'ms-windows.acme.co.uk',
                                 port        => 3389,
                                 domain_name => 'acme',
                                 user        => 'Administrator'}},
                        {ssh => {name => 'Main Server',
                                 host => 'titan.acme.co.uk',
                                 user => 'system'}}]);
$status = $verifier->check(\%data, 'settings');
is($status, '', "Good syntax tree and data");

# Good syntax tree, one bad typed record key in the data (vpn).

%data =
    (config_version => 1.0,
     menu           => [{vpn => {name => 'Desktop',
                                 host => 'desktop.acme.co.uk',
                                 port => 5901}},
                        {rdp => {name        => 'Windows 11',
                                 host        => 'ms-windows.acme.co.uk',
                                 port        => 3389,
                                 domain_name => 'acme',
                                 user        => 'Administrator'}},
                        {ssh => {name => 'Main Server',
                                 host => 'titan.acme.co.uk',
                                 user => 'system'}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/Unexpected single type field record with a type name of `vpn' found at/,
     'Bad key `vpn\' correctly detected');

# Good syntax tree, multiple bad typed record keys and fields in the data.

%data =
    (config_version => 1.0,
     menu           => [{vpn => {name    => 'Desktop',
                                 machinx => 'desktop.acme.co.uk',
                                 port    => 5901}},
                        {rdp => {name        => 'Windows 11',
                                 host        => 'ms-windows.acme.co.uk',
                                 pont        => 3389,
                                 domain_nane => 'acme',
                                 user        => 'Administrator'}},
                        {ssp => {name => 'Main Server',
                                 host => 'titan.acme.co.uk',
                                 user => 'system'}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/`vpn'(?:[^`]+(?:`domain_nane'|`pont')){2}[^`]+`ssp'/s,
     'Bad keys `vpn|domain_nane|pont\' correctly detected');

# Good syntax tree, wrong container (hash instead of an array).

%data =
    (config_version => 1.0,
     menu           => {dummy => {vnc => {name => 'Desktop',
                                          host => 'desktop.acme.co.uk',
                                          port => 5901}}});
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/The settings->menu field is not an array/,
     'Bad hash container correctly detected');

# Good syntax tree, wrong container (array instead of a hash).

%data =
    (config_version => 1.0,
     menu           => [{vnc => ['name']}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/\QThe settings->menu->[0]->vnc field is not a record\E/,
     'Bad array container correctly detected');

# Good syntax tree, absent array container.

%data =
    (config_version => 1.0,
     menu           => 'wrong');
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/\QThe settings->menu field is not an array\E/,
     'Missing array container correctly detected');

# Good syntax tree, container instead of scalar.

%data =
    (config_version => [1.0],
     menu           => [{vnc => {name => 'Desktop',
                                 host => 'desktop.acme.co.uk',
                                 port => 5901}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/\QThe settings->config_version field does not contain a simple value\E/,
     'Bad scalar value correctly detected');

# Good syntax tree, extra unknown field.

%data =
    (config_version => 1.0,
     menu           => [{vnc   => {name  => 'Desktop',
                                   host  => 'desktop.acme.co.uk',
                                   port  => 5901,
                                   extra => 'invalid'}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/The settings-\S+ record contains an invalid field `extra'/,
     'Unknown field correctly detected');

# Good syntax tree, missing mandatory field.

%data =
    (config_version => 1.0,
     menu           => [{vnc   => {name => 'Desktop',
                                   port => 5901}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/The settings-\S+ record does not contain the mandatory field `host'/,
     'Missing mandatory field correctly detected');

# Good syntax tree, missing mandatory field and has an unkown field.

%data =
    (config_version => 1.0,
     menu           => [{vnc   => {name  => 'Desktop',
                                   port  => 5901,
                                   extra => 'invalid'}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/The settings.+record.+mandatory.+ `host'.+invalid.+ `extra'/s,
     'Missing madatory and unknown fields correctly detected');

# Good syntax tree, bad field value.

%data =
    (config_version => 1.0,
     menu           => [{vnc   => {name => 'Desktop',
                                   host => 'desktop.acme.co.uk',
                                   port => '5901x'}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/Unexpected value `5901x' found.+expected value.+between 1 and 65535/,
     'Bad field value correctly detected');

# A syntax tree that contains each type of record in a list (an untyped lone
# record, a key typed record and a single field typed record).

%syntax_tree =
    ('m:config_version' => 'f:0',
     's:options'        =>
         ['i:',
          'R:printable',
          {'m:type' => 's:ssh',
           'm:name' => 'R:printable',
           'm:host' => \@host,
           's:user' => 'R:user_name'}],
     'm:menu'           =>
         [{'t:type'        => 's:rdp',
           'm:name'        => 'R:printable',
           'm:host'        => \@host,
           's:user'        => 'R:user_name',
           's:domain_name' => 'R:hostname'},
          {'m:ssh'         =>
               {'m:name'   => 'R:printable',
                'm:host'   => \@host,
                's:user'   => 'R:user_name'}},
          {'m:telnet'      =>
               {'m:name'   => 'R:printable',
                'm:host'   => \@host,
                's:user'   => 'R:user_name'}},
          {'t:type'        => 's:vnc',
           'm:name'        => 'R:printable',
           'm:host'        => \@host}]);
$verifier->syntax_tree(\%syntax_tree);

# Good syntax tree, good data (testing different types of typed record formats).

%data =
    (config_version => 1.0,
     options        => [26343,
                        'Hello world!',
                        {type => 'ssh',
                         name => 'Main server',
                         host => 'server.acme.co.uk',
                         user => 'system'}],
     menu           => [{type => 'rdp',
                         name => 'Desktop',
                         host => 'desktop.acme.co.uk'},
                        {ssh  =>
                             {name => 'Desktop',
                              host => 'desktop.acme.co.uk'}}]);
$status = $verifier->check(\%data, 'settings');
is($status, '', 'Different record types correctly handled');

# Good syntax tree, good data (many occurrences of one type of a multi-field
# record.

%data =
    (config_version => 1.0,
     options        => [26343,
                        'Hello world!',
                        {type => 'ssh',
                         name => 'Main server',
                         host => 'server.acme.co.uk',
                         user => 'system'},
                        {type => 'ssh',
                         name => 'File server',
                         host => 'nfs.acme.co.uk',
                         user => 'system'}],
     menu           => [{type => 'rdp',
                         name => 'Desktop',
                         host => 'desktop.acme.co.uk'},
                        {ssh  =>
                             {name => 'Desktop',
                              host => 'desktop.acme.co.uk'}},
                        {telnet =>
                             {name => 'Desktop',
                              host => 'desktop.acme.co.uk'}}]);
$status = $verifier->check(\%data, 'settings');
is($status, '', 'Many multi-field records of the same type correctly detected');

# Good syntax tree, good data (many different options for the host scalar
# value).

%data =
    (config_version => 1.0,
     options        => [26343,
                        'Hello world!',
                        {type => 'ssh',
                         name => 'Main server',
                         host => 'server.acme.co.uk',
                         user => 'system'},
                        {type => 'ssh',
                         name => 'File server',
                         host => 'nfs.acme.co.uk',
                         user => 'system'}],
     menu           => [{type => 'rdp',
                         name => 'Desktop',
                         host => '192.168.1.22'},
                        {ssh  =>
                             {name => 'Desktop',
                              host => 'desktop'}}]);
$status = $verifier->check(\%data, 'settings');
is($status, '', 'Many multi-field records of the same type correctly detected');

# A bad syntax tree that has too many untyped records in a list.

%syntax_tree =
    ('m:config_version' => 'f:0',
     'm:menu'           =>
         ['R:printable',
          {'m:type' => 's:rdp',
           'm:name' => 'R:printable',
           'm:host' => \@host,
           's:user' => 'R:user_name'},
          {'m:type' => 's:ssh',
           'm:name' => 'R:printable',
           'm:host' => \@host,
           's:user' => 'R:user_name'}]);
exception_protect(sub { $verifier->syntax_tree(\%syntax_tree); });
like($exception,
     qr/^Illegal syntax.+\(untyped records must be the only record in a list\)/,
     'Multiple untyped records correctly detected');

# A syntax tree that has hosts entries that can contain a scalar value, a list
# or a record.

my @hosts =
    ('l:choice_value',
     'R:hostname',
     'R:ipv4_addr',
     'R:ipv6_addr',
     ['R:hostname', 'R:ipv4_addr','R:ipv6_addr'],
     {'m:hostname'   => 'R:hostname',
      'm:ip_address' => 'R:ipv4_addr'});
%syntax_tree =
    ('m:config_version' => 'f:0',
     's:options'        =>
         ['i:',
          'R:printable',
          {'m:type'  => 's:ssh',
           'm:name'  => 'R:printable',
           'm:hosts' => \@hosts,
           's:user'  => 'R:user_name'}],
     'm:menu'           =>
         [{'t:type'        => 's:rdp',
           'm:name'        => 'R:printable',
           'm:hosts'       => \@hosts,
           's:user'        => 'R:user_name',
           's:domain_name' => 'R:hostname'},
          {'m:ssh'         =>
               {'m:name'   => 'R:printable',
                'm:hosts'  => \@hosts,
                's:user'   => 'R:user_name'}},
          {'m:telnet'      =>
               {'m:name'   => 'R:printable',
                'm:hosts'  => \@hosts,
                's:user'   => 'R:user_name'}},
          {'t:type'        => 's:vnc',
           'm:name'        => 'R:printable',
           'm:hosts'       => \@hosts}]);
$verifier->syntax_tree(\%syntax_tree);

# Good syntax tree, good data (many different options for the host scalar
# value).

%data =
    (config_version => 1.0,
     options        => [26343,
                        'Hello world!',
                        {type  => 'ssh',
                         name  => 'Main server',
                         hosts => 'server.acme.co.uk',
                         user  => 'system'},
                        {type  => 'ssh',
                         name  => 'File server',
                         hosts => '192.168.1.22',
                         user  => 'system'}],
     menu           => [{type   => 'rdp',
                         name   => 'Desktop',
                         hosts  => ['desktop.acme.co.uk', 'server.acme.co.uk']},
                        {ssh    =>
                             {name  => 'Desktop',
                              hosts => {hostname   => 'desktop.acme.co.uk',
                                        ip_address => '192.168.1.24'}}},
                        {telnet =>
                             {name  => 'Desktop',
                              hosts => {hostname   => 'fileserver.acme.co.uk',
                                        ip_address => '192.168.1.22'}}}]);
$status = $verifier->check(\%data, 'settings');
is($status, '', 'Many different forms of hosts file correctly detected');

# Good syntax tree, bad hosts entries.

%data =
    (config_version => 1.0,
     options        => [26343,
                        'Hello world!',
                        {type  => 'ssh',
                         name  => 'Main server',
                         hosts => 'server.acme.co.uk',
                         user  => 'system'},
                        {type  => 'ssh',
                         name  => 'File server',
                         hosts => '192.168.1.22',
                         user  => 'system'}],
     menu           => [{type   => 'rdp',
                         name   => 'Desktop',
                         hosts  => ['desktop.acme.co.uk', '192.168.1.22/24']},
                        {ssh    =>
                             {name  => 'Desktop',
                              hosts => {hostname   => ['desktop.acme.co.uk'],
                                        ip_address => '192.168.1.24'}}},
                        {telnet =>
                             {name  => 'Desktop',
                              hosts => {hostname     => 'fileserver.acme.co.uk',
                                        ip_addresses => '192.168.1.22'}}}]);
$status = $verifier->check(\%data, 'settings');
like($status,
     qr/^Unexpected\ value\ \S+\Q found at settings->menu->[0]->hosts->[1].\E.+?
        \QThe settings->menu->[1]->ssh->hosts->hostname \E.+?
        \QThe settings->menu->[2]->telnet->hosts \E.+?
        \QThe settings->menu->[2]->telnet->hosts->[0] \E.+/sx,
     'Bad hosts field entries correctly detected');

done_testing();

exit(0);
