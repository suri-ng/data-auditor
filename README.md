# Data Auditor

The audit requires a confirmed type for every column. Type inference supplies suggestions, but it never silently chooses types for validation.

Run the current command-line interface with `python app.py path/to/data.csv`. It first displays the dataset summary and all type suggestions. You can accept them together or change selected columns before the remaining checks run. The supported choices are `string`, `integer`, `float`, `boolean`, and `date`.

For a Python caller or Streamlit screen, call `auditor.pipeline.prepare_audit(df)` to obtain the summary and suggestions. After the user confirms or changes the types, call `auditor.pipeline.run_auditor(df, confirmed_types)` with a complete dictionary such as `{"amount": "float", "label": "string"}`. Missing columns, unknown columns, and unsupported types raise `ValueError`.

Category detection automatically checks confirmed string columns for rare values. There are no type-rule or category-rule files. The benchmark scripts contain fixed type labels for their bundled sample datasets.
