package pragma_xmlparse;

use strict;
use warnings;

use XML::Simple;
use Carp;
use File::Basename;
use Cwd 'abs_path';

use Data::Dumper; # DEBUG

use base qw(Exporter);

our @EXPORT     = qw(
    make_vcprofile
    discard_file
);

our @EXPORT_OK  = qw(
);

my $infile;
my $repodir;
my %vcprofile;

### define OpenNebula scripts
### for each virtual cluster type
# my $scriptdir = "/home/ota/work/pragma/pragma-boot";
my $scriptdir = dirname(abs_path(__FILE__));
my %onescripts = (
    beowulf => {
        # frontend => "$scriptdir/pragma_beowulf_fe", 
        # compute  => "$scriptdir/pragma_beowulf_cmp",
        frontend => "$scriptdir/frontend_context", 
        compute  => "$scriptdir/compute_context",
    },
);

# site local attributes
my $domainname     = "hpcc.jp";
my $gateway        = "163.220.56.254";
my $priv_dns       = "192.168.56.240";
my $priv_broadcast = "192.168.57.255";
my $priv_netmask   = "255.255.254.0";
my $priv_network   = "192.168.56.0";
my $pub_dns        = "163.220.2.34 163.220.60.127";
my $pub_broadcast  = "163.220.57.255";
my $pub_netmask    = "255.255.254.0";
my $pub_network    = "163.220.56.0";


# miscellaneous vm attributes
my $tmpdir     = "$ENV{HOME}/tmp";
my $persistent = "no";
my $datastore  = "pragma";
my $mountpoint = "/mnt/file";
my $loopfile   = "/dev/loop0";

### required vm attributes
my @attrs = qw(
    onescript
    mountpoint
    loopfile
    persistent
    imgname
    tmpdir
    imgfile
    datastore
    vcpu
    memory
    nodenum
);



### append miscellaneous vm attributes
sub append_misc {
    # args: ref vm
    my $vm = shift;

    $vm->{persistent} = $persistent;
    $vm->{datastore}  = $datastore;
    $vm->{mountpoint} = $mountpoint;
    $vm->{loopfile}   = $loopfile;
    $vm->{tmpdir}     = $tmpdir;
    $vm->{nodenum}    = 1;

    1;
}

### check nic public or private and append
#sub append_nic {
#    # args: ref vc-in.xml
#    #       ref vm
#    my $inxml = shift;
#    my $vm = shift;
#
#    for my $iface (@{$inxml->{$vm->{nodetype}}[0]{devices}[0]{interface}}) {
#        exists $iface->{subnet} or next; 
#        # I don't know how I should do if 'subnet' is not defined.
#
#        if (lc($iface->{subnet}[0]{name}) eq 'public') {
#            $vm->{ifpub}{name} = $iface->{name};
#            $vm->{ifpub}{type} = $iface->{model}[0]{type};
#        } elsif (lc($iface->{subnet}[0]{name}) eq 'private') {
#            $vm->{ifpriv}{name} = $iface->{name};
#            $vm->{ifpriv}{type} = $iface->{model}[0]{type};
#        }
#    }
#    1;
#}

### get nic information of each nics.
sub get_nic_info {
    my $inxml = shift;
    my $vm    = shift;
    my %nic;
    my $iface;
    if ($vm->{nodetype} eq "frontend") {
        # frontend - eth0
        $iface = $inxml->{$vm->{nodetype}}[0]{domain}[0]{devices}[0]{interface}[0];
        $nic{"eth0"}{network}   = $inxml->{networks}[0]{network}[0]{name};
        $nic{"eth0"}{type}      = $iface->{model}[0]{type};
        $nic{$inxml->{networks}[0]{network}[0]{name}} = "eth0";
        push @{$nic{order}}, "eth0";
        # frontend - eth1 (public)
        $iface = $inxml->{$vm->{nodetype}}[0]{domain}[0]{devices}[0]{interface}[1];
        $nic{"eth1"}{network}   = "public";
        $nic{"eth1"}{type}      = $iface->{model}[0]{type};
        $nic{"public"}          = "eth1";
        push @{$nic{order}}, "eth1";
    } else {
        # compute - eth0
        $iface = $inxml->{$vm->{nodetype}}[0]{domain}[0]{devices}[0]{interface}[0];
        $nic{"eth0"}{network}   = $inxml->{networks}[0]{network}[0]{name};
        $nic{"eth0"}{type}      = $iface->{model}[0]{type};
        $nic{$inxml->{networks}[0]{network}[0]{name}} = "eth0";
        push @{$nic{order}}, "eth0";
    }
    @{$nic{order}} = sort @{$nic{order}};

    \%nic;
}

sub make_profile {
    # args: nodetype(frontend, compute, etc...)
    #       ref vc-in.xml
    my $nodetype = shift;
    my $inxml = shift;
    my %vm;
    
    # required items
    exists $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{source}[0]{file} or do {
        print "\"$nodetype\"'s source file is not defined in $infile\n";
        return 0;
    };
    my $imgfile = $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{source}[0]{file};
    $vm{nodetype} = $nodetype;
    $vm{imgfile} = $repodir . "/" . $imgfile;
    $imgfile =~ s/\..*$//;
    $vm{imgname} = $imgfile;
    $vm{vcpu} = $inxml->{$nodetype}[0]{domain}[0]{vcpu};
    $vm{memory} = $inxml->{$nodetype}[0]{domain}[0]{memory};

    # optional items
    exists $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{format}
        and $vm{diskformat} = $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{format};
    exists $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{bus}
        and $vm{diskbus} = $inxml->{$nodetype}[0]{domain}[0]{devices}[0]{disk}[0]{bus};

    $vm{nic} = get_nic_info($inxml, \%vm);
    #append_nic($inxml, \%vm);
    append_misc(\%vm);

    # add appropriate startup-script
    $vm{onescript} = $onescripts{$vcprofile{vctype}}{$nodetype};

    check_attributes(\%vm) or return 0;

    return \%vm;
}

### chech attrivutes
sub check_attributes {
    my $vm = shift;
    map {
        exists $vm->{$_} or do {
            print "attrivute '$_' is not defined\n";
            return 0;
        };
    } @attrs;
    1;
}

### discard file.
sub discard_file {
    for my $file (@_) {
        unlink($file) or do {
            warn "unlink $file failed. $!";
            return 0;
        };
    }
    1;
}

### make virtual cluster profile
sub make_vcprofile {
    $infile = shift or do {
        print "[make_vcprofile] invalid argument.\n";
        return 0;
    };
    unless (-f $infile) {
        print "[make_vcprofile] $infile is not valid file.\n";
        return 0;
    }


    ### get information from in.xml
    my $inxml = eval {XMLin($infile, ForceArray => 1, SuppressEmpty => undef, keyattr => []);};
    if ($@) {
        print "[make_vcprofile] XML parse error\n";
        print "$@";
        return 0;
    }

    ### get path to images
    $repodir = dirname($infile);

    if ($inxml->{virtualization}[0]{engine} ne "kvm") {
        print "[make_vcprofile] we support only \"virtualization engine='kvm'\", abort\n";
        return 0;
    }

    ### check virtual cluster type
    ### e.g. beowulf, etc...
    exists $inxml->{type} or do {
        print "[make_vcprofile] 'vc type'not defined in $infile\n";
        return 0;
    };
    ### define virtual cluster type into %vcprofile
    if (lc($inxml->{type}) eq "local beowulf") {
        $vcprofile{vctype} = 'beowulf';
    }

    ### make vircual cluster profile.

    ### in case of 'beowulf' vctype, nodetype uses 'frontend' and 'compute'.
    if ($vcprofile{vctype} eq 'beowulf') {
        $vcprofile{node}{frontend} = make_profile('frontend', $inxml) or return 0;
        $vcprofile{node}{compute}  = make_profile('compute', $inxml)  or return 0;
    }

    ### append site local attrivutes.
    $vcprofile{sitelocal}{domainname}     = $domainname;
    $vcprofile{sitelocal}{gateway}        = $gateway;
    $vcprofile{sitelocal}{priv_dns}       = $priv_dns;
    $vcprofile{sitelocal}{priv_broadcast} = $priv_broadcast;
    $vcprofile{sitelocal}{priv_netmask}   = $priv_netmask;
    $vcprofile{sitelocal}{priv_network}   = $priv_network;
    $vcprofile{sitelocal}{pub_dns}        = $pub_dns;
    $vcprofile{sitelocal}{pub_broadcast}  = $pub_broadcast;
    $vcprofile{sitelocal}{pub_netmask}    = $pub_netmask;
    $vcprofile{sitelocal}{pub_network}    = $pub_network;

    \%vcprofile;
}

1;
__END__
