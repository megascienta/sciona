# SCIONA Reducer Validation Report

## Executive Summary

- repo=sciona
- sampled_nodes=250
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.4766780784249024
- contract_recall_mean=0.8408495744022059
- full_precision_mean=0.5073798328108673
- full_recall_mean=0.239661942131992
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.4766780784249024`
- in_contract_recall_mean: `0.8408495744022059`
- misses_out_of_contract_rate: `0.9141914191419142`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.5073798328108673`
- in_contract_recall_mean: `0.239661942131992`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.4766780784249024 < 0.95
- recall_mean 0.8408495744022059 < 0.9
- group python::method precision 0.0 < 0.85
- group python::module precision 0.7737507603050577 < 0.85
- group python::class precision 0.0 < 0.85
- group python::function precision 0.1 < 0.85

## Group Metrics

- db_equivalence python::method: precision=`1.0`, recall=`1.0`
- db_equivalence python::module: precision=`1.0`, recall=`1.0`
- db_equivalence python::class: precision=`1.0`, recall=`1.0`
- db_equivalence python::function: precision=`1.0`, recall=`1.0`
- contract python::method: precision=`0.0`, recall=`None`
- contract python::module: precision=`0.7737507603050577`, recall=`0.8331487473571513`
- contract python::class: precision=`0.0`, recall=`None`
- contract python::function: precision=`0.1`, recall=`1.0`
- full python::method: precision=`0.0`, recall=`None`
- full python::module: precision=`0.7737507603050577`, recall=`0.24700935533099524`
- full python::class: precision=`0.0`, recall=`None`
- full python::function: precision=`0.24`, recall=`0.17975226527858107`

## Edge Type Breakdown

- db_equivalence calls: tp=`180`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`678`, fp=`0`, fn=`0`
- contract calls: tp=`3`, fp=`177`, fn=`0`
- contract imports: tp=`210`, fp=`468`, fn=`52`
- full calls: tp=`12`, fp=`168`, fn=`166`
- full imports: tp=`210`, fp=`468`, fn=`441`

## Failure Examples (DB Equivalence)

- sciona.src.sciona.code_analysis.core.extract.languages.python_analyzer.PythonAnalyzer.analyze: recall=1.0
- sciona.src.sciona.runtime.agents_setup: recall=1.0
- sciona.src.sciona.code_analysis.core.engine.BuildEngine: recall=1.0
- sciona.src.sciona.pipelines.exec: recall=1.0
- sciona.tests.helpers.Diagnostics: recall=1.0
- sciona.experiments.reducers.reducer_validation.main: recall=1.0
- sciona.src.sciona.code_analysis: recall=1.0
- sciona.src.sciona.code_analysis.tools.profile_introspection_typescript._TypeScriptInspector._scan: recall=1.0
- sciona.src.sciona.code_analysis.core.extract.languages.typescript: recall=1.0
- sciona.experiments: recall=1.0

## Failure Examples (Contract)

- sciona.src.sciona.code_analysis: recall=0.0
- sciona.src.sciona.reducers.grounding: recall=0.0
- sciona.src.sciona.reducers.helpers: recall=0.0
- sciona.src.sciona.code_analysis.core.extract: recall=0.0
- sciona.src.sciona.code_analysis.analysis: recall=0.0
- sciona.src.sciona.reducers: recall=0.0
- sciona.src.sciona.data_storage.core_db.connect: recall=0.0
- sciona.src.sciona.runtime.config.io: recall=0.6666666666666666
- sciona.src.sciona.cli.commands.register_build: recall=0.6666666666666666
- sciona.src.sciona.cli.search: recall=0.6666666666666666

## Failure Examples (Full)

- sciona.tests.pipelines.test_snapshots: recall=0.0
- sciona.src.sciona.pipelines.exec: recall=0.0
- sciona.tests.reducers.test_core_reducers: recall=0.0
- sciona.src.sciona.code_analysis: recall=0.0
- sciona.tests.conftest.cli_app: recall=0.0
- sciona.tests.helpers: recall=0.0
- sciona.experiments.reducers.reducer_validation: recall=0.0
- sciona.tests.code_analysis.test_snapshot_tools: recall=0.0
- sciona.tests.helpers._node_entry: recall=0.0
- sciona.tests.data_storage.test_artifact_rollups_fk: recall=0.0
