# Star Detection

[Back to README](/README.md)

## Overview 
Star detection identifies point sources in NEOSSat images and cross-references them against the SIMBAD astronomical database to classify detected objects by type (stars, galaxies, nebulae, etc.).

## How to run
```bash
make stars
neossat-cli --stars
POST /preprocessing
```

## Output
