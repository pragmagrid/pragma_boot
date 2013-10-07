#!/usr/bin/env perl

use strict;
use warnings;
use File::Copy qw(copy);
use File::Basename;
use Data::Dumper;

use pragma_xmlparse qw( make_vcprofile );

### Unix command
my $mount      = "/bin/mount";
my $umount     = "/bin/umount";
my $losetup    = "/sbin/losetup";
my $kpartx     = "/sbin/kpartx";
my $gunzip     = "/bin/gunzip";
my $bunzip2    = "/usr/bin/bunzip2";

my $myname     = basename($0);
my $usage = "usage: $myname vc-in.xml";

#--------------------------------------------------------------------
# injection "loopfile" "mountpoint";
#--------------------------------------------------------------------
sub injection {
    my $onescript  = shift;
    my $mountpoint = shift;
    my @mappedfiles = @_;

    if (! -d $mountpoint) {
        print "[makeover] mount pint: $mountpoint does not exist\n";
        return 0;
    }

    for my $path (@mappedfiles) {
        ### mount filesystem.
        ### if cannot mount, skip and try next;
        sleep(1);  # HACK: need to delay mounting a little bit.
        !system $mount, $path, $mountpoint or next;


        if (-f "$mountpoint/etc/redhat-release" or -f "$mountpoint/redhat-release") {

            my $etcdir = -f "$mountpoint/etc/redhat-release" ?
            "$mountpoint/etc/" :
            "$mountpoint";

            ### do for RHEL
            install_scripts_rhel($etcdir, $onescript);

            ### and unmount filesystem and return.
            !system $umount, $mountpoint       or do {
                warn "[makeover] umount $mountpoint failed";
                return 0;
            };
            return 1;
        }

        ### for another distoribution
        ### ...

        ### Distribution check and injection done.

        ### any distribution's sign has not found on this partition.
        !system $umount, $mountpoint       or do {
            warn "[makeover] umount $mountpoint failed";
            return 0;
        };
    }
    # Probably injection process has not succeeded. 
    return 0;
}

#--------------------------------------------------------------------
# install_scripts_rhel "/path/to/target_etc_directory";
#--------------------------------------------------------------------
sub install_scripts_rhel {
    my $etcdir     = shift;
    my $onescript  = shift;

    my $priority       = "S05";
    my $onescript_name = basename($onescript);

    ### install scripts.
    copy($onescript, "$etcdir/rc.d/init.d")
        or warn "[makeover] copy $onescript failed.";
    chmod 0755, "$etcdir/rc.d/init.d/$onescript_name"
        or warn "[makeover] chmod 0755 $onescript_name failed.";

    ### delete old symbolic links.
    my @oldfiles = <$etcdir/rc.d/rc*.d/*$onescript_name>;
    if (@oldfiles) {
        print scalar(@oldfiles) . " old file(s) found.\n";
        map {print "  ($_)\n";} @oldfiles;
        my $deleted = unlink @oldfiles
            or warn "[makeover] unlink failed.";
        $deleted    and print "$deleted old file(s) deleted.\n";
    }

    my $pwd = `pwd`;
    chomp $pwd;

    ### create new symbolic link 
    ### e.g.  ln -s ../init.d/one_ipaddress_rhel S01one_ipaddress_rhel
    for my $rcNd (qw( rc3.d rc5.d )) {
        chdir "$etcdir/rc.d/$rcNd"
            or warn "[makeover] chdir $etcdir/rc.d/$rcNd failed.";
        symlink "../init.d/$onescript_name", "$priority$onescript_name"
            or warn "[makeover] create symlink $etcdir/rc.d/$rcNd failed: $!";
    }

    chdir $pwd or warn "[makeover] chdir $pwd failed.";

    1;
}

#--------------------------------------------------------------------
# get_available_loopfile;
# get an available (appropriate) loopback device
#--------------------------------------------------------------------
sub get_available_loopfile {
    my $loopfile = shift;

    my @devnames = `$losetup -a`;
    if (@devnames) {
        my $current = pop @devnames;
        $current =~ /^(.*loop)(\d+)/;
        my $devnum = $2 + 1;
        $loopfile = $1 . $devnum;
    }
    if (! -b $loopfile) {
        warn "[makeover] invalid loop device: $loopfile\n";
        return 0;
    }
    $loopfile;
}

#--------------------------------------------------------------------
# get_mapped_files "loopfile";
#--------------------------------------------------------------------
sub get_mapped_files {
    my $loopfile = shift;

    my @mappedfiles = `$kpartx -l $loopfile`  or do {
        warn "[makeover] kpartx -l failed";
        return ();
    };
    chomp @mappedfiles;
    return map { /(^loop\d+p\d+)/; "/dev/mapper/$1"; } @mappedfiles;
}

#--------------------------------------------------------------------
# losetup_attach "loopfile" "imagefile";
#--------------------------------------------------------------------
sub losetup_attach {
    my $loopfile   = shift;
    my $imgfile    = shift;

    print "[makeover] attach $imgfile to $loopfile\n";
    my $ret = system $losetup, $loopfile, $imgfile;
    if ($ret != 0) {
        warn "[makeover] losetup failed";
        return 0;
    }
    1;
}

#--------------------------------------------------------------------
# kpartx_attach "loopfile";
#--------------------------------------------------------------------
sub kpartx_attach {
    my $loopfile = shift;

    my @mappedfiles = `$kpartx -av $loopfile 2>&1`  or do {
        warn "[makeover] kpartx -av failed";
        return ();
    };
    grep /read error/, @mappedfiles          and do {
        warn "[makeover] incorrect vm imagefile?";
        return ();
    };
    chomp @mappedfiles;
    return map { /^add map (loop\d+p\d+)/; "/dev/mapper/$1"; } @mappedfiles;
}

#--------------------------------------------------------------------
# attach_file 
#--------------------------------------------------------------------
sub attach_file {
    my $loopfile   = shift;
    my $imgfile    = shift;
    my @mappedfiles;

    losetup_attach($loopfile, $imgfile)        or return ();
    @mappedfiles = kpartx_attach($loopfile)  or do {
        warn "[makeover] kpartx_attach failed";
        losetup_detach($loopfile);
        return ();
    };
    return @mappedfiles;
}

#--------------------------------------------------------------------
# losetup_detach "loopfile";
#--------------------------------------------------------------------
sub losetup_detach {
    my $loopfile = shift;

    my $ret = system $losetup, "-d", $loopfile;
    if ($ret != 0) {
        warn "[makeover] losetup -d failed";
        return 0;
    }
    1;
}

#--------------------------------------------------------------------
# kpartx_detach "loopfile";
#--------------------------------------------------------------------
sub kpartx_detach {
    my $loopfile = shift;

    my $ret = system $kpartx, "-d", $loopfile;
    if ($ret != 0) {
        warn "[makeover] kpartx -d failed";
        return 0;
    }
    1;
}

#--------------------------------------------------------------------
# detach_file "loopfile";
#--------------------------------------------------------------------
sub detach_file {
    my $loopfile = shift;
    my $ret1 = 0;
    my $ret2 = 0;

    sleep 1;
    $ret1 = kpartx_detach($loopfile);
    $ret2 = losetup_detach($loopfile);
    if ($ret1 == 0 or $ret2 == 0) {
        return 0;
    }
    1;
}

#--------------------------------------------------------------------
# file decompress;
#--------------------------------------------------------------------
sub decomp_file {
    my $file = shift;
    if ($file =~ /^(\S+)\.gz$/) {
        ### Gzip-ed file.
        !system("$gunzip $file")   or do {
            warn "[makeover] $gunzip $file failed";
            return 0;
        };
        $file = $1;
    } elsif ($file =~ /^(\S+)\.bz2$/) {
        ### Bzip2-ed file.
        !system("$bunzip2 $file")  or do {
            warn "[makeover] $bunzip2 $file failed";
            return 0;
        };
        $file = $1;
    }
    $file;
}

#--------------------------------------------------------------------
# makeover image files for beowulf cluster.
#--------------------------------------------------------------------
sub makeover {
    my $vcprofile = shift;

    # makeover each vm imagefile.
    for my $vm (values %{$vcprofile->{node}}) {
        #print Dumper($vm); # DEBUG

        my $loopfile = get_available_loopfile($vm->{loopfile}) or do {
            print "loopfile is not available\n";
            return 0;
        };

        # my $decompressed_image = decomp_file($vm->{imgfile})

        # my @mappedfiles = attach_file($loopfile, $decompressed_image) or do {
        my @mappedfiles = attach_file($loopfile, $vm->{imgfile}) or do {
            print "file attach failed\n";
            return 0;
        };

        injection($vm->{onescript}, $vm->{mountpoint}, @mappedfiles)
            or print "injection failed\n";

        detach_file($loopfile) or do {
            print "file detach failed\n";
            return 0;
        };
    }
    1;
}


### main
### vc-in.xml file check.
my $infile = shift or do {
    print "$usage\n";
    exit 1;
};
unless (-f $infile) {
    print "$infile is not valid file.\n$usage\n";
    exit 1;
}

my $vcprofile = make_vcprofile($infile) or do {
    print "$infile parse failed\n";
    exit 1;
};

#print Dumper($vcprofile); # DEBUG

makeover($vcprofile) or die;

1;
__END__
# $Id$
