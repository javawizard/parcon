#!/usr/bin/perl

# Thanks to Alyx Wolcott for this script

use strict;
use warnings;
use File::Slurp;

my $original = <<EOSEARCH;
</head>
EOSEARCH

my $change = <<EOCHANGE;
<script type="text/javascript">

  var _gaq = _gaq || [];
// START JCP ADD
  if(window.location.href.indexOf("http://www.opengroove.org/") == 0) {
// END JCP ADD
  _gaq.push(['_setAccount', 'UA-6079740-6']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();
// START JCP ADD
}
// END JCP ADD

</script>
</head>
EOCHANGE

chomp($original);
chomp($change);

my $file = read_file($ARGV[0]);

$file =~ s/$original/$change/;

open(my $out, '>', $ARGV[1]);

print {$out} $file;

