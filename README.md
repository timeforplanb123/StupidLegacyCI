# StupidLegacyCI


Overview:
- Gitlab pipeline uses local runner - "docker0"
- The job `update_cache` works by schedule and updates the necessary Python packages
- The job `compare_commits` compares YAMLs of the previous and current commit with `git diff`. The result - YAMLs list where network parameters have changed
- The job `tests` run Pytest with stdout parameter and short traceback. As instance, in repository we have single test - `test_snmp.py`. It's template for any other tests
- The job `run` run YAML Handler, `stupid_ci.py`, for creating config based on these YAMLs
