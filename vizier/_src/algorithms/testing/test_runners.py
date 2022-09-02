"""Test runners for algorithms."""
from typing import Any, Callable, Collection, Optional, Sequence

from absl import logging
import attr
import numpy as np
from vizier import algorithms as vza
from vizier import benchmarks
from vizier import pythia
from vizier import pyvizier as vz


@attr.define
class RandomMetricsRunner:
  """Generates completed `Trial`s with random metrics.

  EXAMPLE: This method can be used for smoke testing a `Designer`.
  ```
  from vizier._src.algorithms.testing import test_runners
  from vizier.testing import test_studies
  from vizier import pyvizier as vz

  study_config = vz.ProblemStatement(
      test_studies.flat_space_with_all_types(),
      [vz.MetricInformation(
          'objective',
          goal=vz.ObjectiveMetricGoal.MAXIMIZE)],
      validate_parameters=True)
  test_runners.run_with_random_metrics(my_designer, study_config)
  ```

  EXAMPLE: This method can be used for generating a large number of trials
  to be used as a test dataset.
  ```
  # (Continued from the above code block)
  from vizier._src.algorithms.designers import random
  trials = test_runners.run_with_random_metrics(
      random.RandomDesigner(study_config.search_space),
      study_config,
      validate_parameters=False)
  ```

  run_* methods run a suggest-update loop, completing suggestions with
  random metric values and then return all generated trials.
  The random values are sampled from uniform distribution over the metric's
  specified range. If the minimum or maximum is not specified, it defaults to
  -10 and +10 respectively.

  Attributes:
    problem: Problem definition.
    iters: Number of suggest-update iterations.
    batch_size: Number of suggestions to ask in each suggest() call.
    seed: Random seed for generating metrics.
    verbose: Increase the verbosity to see more logs.
    validate_parameters: If True, check if the suggested trials are valid in the
      search space.
  """
  problem: vz.ProblemStatement = attr.field()
  iters: int = attr.field(default=5)
  batch_size: Optional[int] = attr.field(default=1, kw_only=True)
  seed: Any = attr.field(default=None, kw_only=True)
  verbose: int = attr.field(default=0, kw_only=True)
  validate_parameters: bool = attr.field(default=False, kw_only=True)

  def _run(
      self,
      algorithm: benchmarks.AlgorithmRunnerProtocol) -> Collection[vz.Trial]:
    """Implementation of run methods."""
    rng = np.random.RandomState(self.seed)
    all_trials = []
    for it in range(self.iters):
      suggestions = algorithm.suggest(self.batch_size)
      if not suggestions:
        logging.info(
            'Preemptively finished at iteration %s'
            'because designer returned nothing.', it)
        break
      trials = []
      for suggestion in suggestions:
        if self.validate_parameters:
          self.problem.search_space.assert_contains(suggestion.parameters)
        measurement = vz.Measurement()
        for mi in self.problem.metric_information:
          measurement.metrics[mi.name] = rng.uniform(
              mi.min_value_or(lambda: -10.), mi.max_value_or(lambda: 10.))
        trials.append(
            suggestion.to_trial(len(trials) + 1).complete(measurement))
        if self.verbose:
          logging.info('At iteration %s, trials suggested and evaluated:\n%s',
                       it, trials)
      algorithm.post_completion_callback(vza.CompletedTrials(trials))
      all_trials.extend(trials)
    return all_trials

  def run_policy(self, policy_factory: Callable[[pythia.PolicySupporter],
                                                pythia.Policy]):
    """Run the policy generated by policy_factory."""
    runner = pythia.InRamPolicySupporter(self.problem)
    policy = policy_factory(runner)
    return self._run(benchmarks.PolicyRunnerProtocol(policy, runner))

  def run_designer(self, designer: vza.Designer):
    """Run the specified $designer."""
    runner = pythia.InRamPolicySupporter(self.problem)
    return self._run(benchmarks.DesignerRunnerProtocol(designer, runner))


def run_with_random_metrics(
    designer: vza.Designer,
    problem: vz.ProblemStatement,
    /,
    iters: int = 5,
    *,
    batch_size: Optional[int] = 1,
    seed: Any = None,
    verbose: int = 0,
    validate_parameters: bool = False) -> Sequence[vz.Trial]:
  """DEPRECATED. Use RandomMetricsRunner.run_designer()."""
  return RandomMetricsRunner(
      problem,
      iters,
      batch_size=batch_size,
      seed=seed,
      verbose=verbose,
      validate_parameters=validate_parameters).run_designer(designer)
