import numpy as np
from scipy.optimize import linprog

from core.exceptions import OptimizationError
from schema.schema import FeedFormulationRequest
from services.feed_optimization_service import FeedOptimizationService


DIAGNOSTIC_TOLERANCE = 0.0001
BOUND_TOLERANCE = 1e-7
INCLUSION_PERCENTAGE = 0.001


class FeedOptimizationV2Service:
    def __init__(self, primary_solver: FeedOptimizationService | None = None):
        self.primary_solver = primary_solver or FeedOptimizationService()

    def formulate(self, request: FeedFormulationRequest) -> dict:
        response = self.primary_solver.formulate(request)
        if response["status"] == "success":
            return response

        diagnostic = self._closest_bounded_formulation(request)
        response.update(diagnostic)
        return response

    def _closest_bounded_formulation(
        self, request: FeedFormulationRequest
    ) -> dict:
        costs = np.array(
            [ingredient.cost_per_kg for ingredient in request.ingredients]
        )
        nutrient_matrix = np.array(
            [
                [ingredient.protein_percent for ingredient in request.ingredients],
                [ingredient.energy_me for ingredient in request.ingredients],
                [ingredient.calcium_percent for ingredient in request.ingredients],
                [
                    ingredient.phosphorus_percent
                    for ingredient in request.ingredients
                ],
            ]
        )
        constraint_matrix = np.vstack(
            (np.ones((1, len(request.ingredients))), nutrient_matrix)
        )
        targets = np.array(
            [
                1.0,
                request.nutrient_requirements.protein_percent,
                request.nutrient_requirements.energy_me,
                request.nutrient_requirements.calcium_percent,
                request.nutrient_requirements.phosphorus_percent,
            ]
        )
        minimums = np.array(
            [ingredient.min_percentage for ingredient in request.ingredients]
        )
        maximums = np.array(
            [ingredient.max_percentage for ingredient in request.ingredients]
        )

        constraint_count = len(targets)
        ingredient_count = len(request.ingredients)
        normalized_weights = 1 / np.maximum(np.abs(targets), 1.0)
        slack_objective = np.hstack(
            (
                np.zeros(ingredient_count),
                normalized_weights,
                normalized_weights,
            )
        )
        equality_matrix = np.hstack(
            (
                constraint_matrix,
                np.eye(constraint_count),
                -np.eye(constraint_count),
            )
        )
        bounds = list(zip(minimums, maximums)) + [
            (0, None)
        ] * (constraint_count * 2)

        try:
            closest = linprog(
                slack_objective,
                A_eq=equality_matrix,
                b_eq=targets,
                bounds=bounds,
                method="highs",
            )
        except Exception as exc:
            raise OptimizationError("Diagnostic optimization failed") from exc

        if not closest.success or closest.x is None:
            raise OptimizationError("Diagnostic optimization failed")

        cost_objective = np.hstack(
            (costs, np.zeros(constraint_count * 2))
        )
        try:
            least_cost = linprog(
                cost_objective,
                A_ub=np.array([slack_objective]),
                b_ub=np.array([float(closest.fun) + 1e-9]),
                A_eq=equality_matrix,
                b_eq=targets,
                bounds=bounds,
                method="highs",
            )
        except Exception:
            least_cost = None

        solution = (
            least_cost.x
            if least_cost is not None and least_cost.success
            else closest.x
        )
        percentages = solution[:ingredient_count]
        achieved = constraint_matrix @ percentages
        diagnostics = self._constraint_diagnostics(achieved, targets)

        return {
            "ingredient_composition": self._ingredient_composition(
                request, percentages, costs
            ),
            "constraint_diagnostics": diagnostics,
            "failed_constraints": [
                name
                for name, diagnostic in diagnostics.items()
                if diagnostic["status"] != "met"
            ],
            "summary": {
                "total_ingredient_percentage": round(
                    float(achieved[0] * 100), 6
                ),
                "active_ingredients_count": sum(
                    float(value * 100) > INCLUSION_PERCENTAGE
                    for value in percentages
                ),
                "cost_per_kg": round(float(costs @ percentages), 4),
                "normalized_violation_score": round(float(closest.fun), 8),
                "formulation_feasible": False,
            },
        }

    @staticmethod
    def _constraint_diagnostics(
        achieved: np.ndarray, targets: np.ndarray
    ) -> dict[str, dict]:
        names = [
            "total_ingredient_percentage",
            "protein_percent",
            "energy_me",
            "calcium_percent",
            "phosphorus_percent",
        ]
        diagnostics = {}
        for index, name in enumerate(names):
            scale = 100 if index == 0 else 1
            achieved_value = float(achieved[index] * scale)
            required_value = float(targets[index] * scale)
            difference = achieved_value - required_value
            if abs(difference) <= DIAGNOSTIC_TOLERANCE:
                constraint_status = "met"
            elif difference < 0:
                constraint_status = "under"
            else:
                constraint_status = "over"
            diagnostics[name] = {
                "achieved": round(achieved_value, 6),
                "required": round(required_value, 6),
                "difference": round(difference, 6),
                "status": constraint_status,
            }
        return diagnostics

    @staticmethod
    def _ingredient_composition(
        request: FeedFormulationRequest,
        percentages: np.ndarray,
        costs: np.ndarray,
    ) -> list[dict]:
        composition = []
        for index, ingredient in enumerate(request.ingredients):
            fraction = float(percentages[index])
            percentage = fraction * 100
            at_minimum = (
                abs(fraction - ingredient.min_percentage) <= BOUND_TOLERANCE
            )
            at_maximum = (
                abs(fraction - ingredient.max_percentage) <= BOUND_TOLERANCE
            )
            issues = []
            if at_minimum:
                issues.append("minimum_bound_active")
            if at_maximum:
                issues.append("maximum_bound_active")

            if percentage <= INCLUSION_PERCENTAGE:
                ingredient_status = "excluded"
            elif at_minimum:
                ingredient_status = "at_minimum"
            elif at_maximum:
                ingredient_status = "at_maximum"
            else:
                ingredient_status = "included"

            composition.append(
                {
                    "name": ingredient.name,
                    "percentage": round(percentage, 4),
                    "cost_contribution": round(
                        float(costs[index] * fraction), 4
                    ),
                    "included": percentage > INCLUSION_PERCENTAGE,
                    "status": ingredient_status,
                    "issues": issues,
                }
            )
        return composition
