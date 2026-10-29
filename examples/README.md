# Examples

- `gdpb_example.py` is Appendix B of the GDP-B Cookbook, verbatim. It needs only numpy and scipy
  and reproduces the cookbook's worked numbers (median 50.34, capped mean 100.41 at a $500 cap,
  200 of 200 bootstrap fits):

      python gdpb_example.py --make-example --folder example --bootstrap 200

- `config.yaml` drives the full package pipeline on a simulated multi-item survey:

      gdpb simulate . && gdpb run config.yaml

- The package reads the Appendix B files directly. After running the script above:

      gdpb run example/config.json   # after adding responses/items/output keys, see tests/test_pipeline.py

All data here are synthetic.
