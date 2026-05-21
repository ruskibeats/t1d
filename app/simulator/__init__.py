"""T1D Companion Simulator — synthetic patient pipeline for detector evaluation.

Modules
-------
anchors : 12 anchor profiles with parameter ranges
patient_factory : generate PatientConfig from anchors
day_context : generate daily event schedules
glucose_engine : physiological CGM trace simulation
writeback : write synthetic data into production tables
truth_labels : plant hidden ground-truth labels
evaluator : score detector output against truths
service : orchestrator for end-to-end runs
schemas : Pydantic models for the simulator domain
models : SQLAlchemy ORM models (sim_runs, sim_users, sim_hidden_truths, sim_detector_scores)
"""

__version__ = "0.1.0"
