#!/usr/bin/perl

# This script, like pydoc-analytics.pl, provided by Alyx Wolcott, with some
# modifications by Alexander Boyd to template the sidebar as well as the main
# page content.

use strict;
use warnings;
use File::Slurp;

my $outer = read_file($ARGV[0]);
my $inner = read_file($ARGV[1]);
my $sidebar = read_file($ARGV[2]);

chomp $inner;

$outer =~ s!INSERT_CONTENT_HERE!$inner!;
$outer =~ s!INSERT_SIDEBAR_HERE!$sidebar!;

open(my $new, '>', $ARGV[3]);

print {$new} $outer;

