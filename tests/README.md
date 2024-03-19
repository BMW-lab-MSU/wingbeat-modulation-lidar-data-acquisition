# Running tests

Before running any of these tests, make sure the `wingbeat_lidar` package has been installed.

## Unit tests
Run the unit tests with
```
python -m unittest unit_tests
```

## Integration tests
Run the integration tests with
```
python -m unittest integration_tests
```

The integration tests require the digitizer to be installed in the computer.
Some of the integration tests require a function generator to be connected to the digitizer.
**TODO**: document function generator settings
