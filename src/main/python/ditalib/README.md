# Python DITA support library

Provides support for processing DITA content with full key
and DITAVAL awareness.

Provides the following services:

* Map resolution: resolve trees of maps into a single in-memory XML document with all submap information preserved and (optionally) with metadata propagated per the DITA 1.3/2.0 rules.
* Key space construction and management: Construct DITA 1.3/2.0 key spaces and make them available for key resolution and key space reporting.
* DITA processing utilities, including DITA @class value checking, topicref type checking (topichead, topicgroup, map reference, etc.), and reference resolution.
* DITAVAL filtering and reporting: Construct DITA filters that can be used to filter DITA elements and report on the details of a filter (conditions, actions, etc.)
* General error collection and reporting facilities beyond Python's built-in logging.
* Generic XML processing utilities, including configuring parsers with Open Toolkit-managed entity resolution libraries.

## Configuration

In order to create parsers initialized with an Open Toolkit entity catalog you need to tell ditalib where to find the Open Toolkit, which you can do in several ways:

* Create a file `.build.properties` in your home directory (`$HOME`) with the entry `dita.ot.dir`:
  ```
  dita.ot.dir=${user.home}/ditaot/ditaot-3_7_4
  ```

  This file can have other properties.
* Set the environment variable `DITA_OT_DIR` with the path to the OT:
  ```
  % export DITA_OT_DIR="{HOME}/ditaot/ditaot-3_7_4"
  ```

* (TBD) Run the `