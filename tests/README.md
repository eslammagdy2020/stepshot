# StepShot automated tests

Run from the project root:

```bash
pip install -r requirements-test.txt
pytest
```

Useful options:

```bash
pytest -m acceptance          # PRD acceptance criteria only
pytest tests/test_services    # Service layer only
```
