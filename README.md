# OpenCCK IPv4 lists mirror

This repository mirrors the public IPv4 lists published by the main and
Russian OpenCCK portals. Upstream attribution: [rekryt/iplist](https://github.com/rekryt/iplist).

`lists/<portal>/<site-or-group>/<name>.txt` contains one IPv4 prefix per line.
The lists come from the OpenCCK export endpoints. The mirror retains the last
validated copy when a source temporarily returns an empty or invalid export.

Run `python3 sync.py` from a network that can reach both OpenCCK portals to
update the mirror. Only commit the resulting files after validation succeeds.
