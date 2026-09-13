import numpy as np
from scipy.optimize import linprog

from core.exceptions import OptimizationError, ValidationError
from schema.feed_v3 import FeedFormulationV3Request
from schema.schema import FeedFormulationRequest


class FeedOptimizationService:
    nutrient_fields = (
        "protein_percent",
        "energy_me",
        "calcium_percent",
        "phosphorus_percent",
    )

    def formulate(
        self, request: FeedFormulationRequest | FeedFormulationV3Request
    ) -> dict:
        if not request.ingredients:
            raise ValidationError("At least one ingredient must be provided")

        names = [ingredient.name for ingredient in request.ingredients]
        costs = np.array(
            [ingredient.cost_per_kg for ingredient in request.ingredients]
        )
        nutrient_matrix = np.array(
            [
                [getattr(ingredient, name) for ingredient in request.ingredients]
                for name in self.nutrient_fields
            ]
        )
        nutrient_targets = np.array(
            [
                getattr(request.nutrient_requirements, name)
                for name in self.nutrient_fields
            ]
        )
        minimums = np.array(
            [ingredient.min_percentage for ingredient in request.ingredients]
        )
        maximums = np.array(
            [ingredient.max_percentage for ingredient in request.ingredients]
        )

        if np.any(minimums < 0) or np.any(maximums > 1):
            raise ValidationError("Ingredient percentages must be between 0 and 1")
        if np.any(minimums > maximums):
            raise ValidationError(
                "Minimum percentage cannot be greater than maximum percentage"
            )

        equality_matrix = np.vstack(
            (np.ones((1, len(names))), nutrient_matrix)
        )
        equality_targets = np.hstack(([1.0], nutrient_targets))

        try:
            result = linprog(
                costs,
                A_eq=equality_matrix,
                b_eq=equality_targets,
                bounds=list(zip(minimums, maximums)),
                method=request.optimization_method,
            )
        except Exception as exc:
            raise OptimizationError("Optimization failed") from exc

        response = self._base_response(request)
        if not result.success:
            response.update(
                {
                    "status": "failure",
                    "detail": "No optimal solution found.",
                    "error_details": {
                        "solver_status_code": int(result.status),
                        "solver_message": str(result.message),
                        "possible_causes": [
                            "Nutrient requirements may be impossible to meet with given ingredients",
                            "Ingredient constraints may be too restrictive",
                            "Cost optimization may have no feasible solution",
                        ],
                        "suggestions": [
                            "Review nutrient requirements and ensure they are achievable",
                            "Check ingredient min/max percentage constraints",
                            "Consider adding more ingredient options",
                            "Verify ingredient nutrient compositions are correct",
                        ],
                    },
                    "formulation_feasible": False,
                }
            )
            return response

        percentages = result.x * 100
        nutrient_values = nutrient_matrix @ result.x
        cost_breakdown = costs * result.x
        response.update(
            {
                "status": "success",
                "message": "Optimal feed formulation found.",
                "optimization_details": {
                    "solver_status": str(result.message),
                    "iterations": int(getattr(result, "nit", 0)),
                    "total_cost_per_kg": round(float(result.fun), 4),
                },
                "ingredient_composition": [
                    {
                        "name": names[index],
                        "percentage": round(float(percentages[index]), 4),
                        "cost_contribution": round(
                            float(cost_breakdown[index]), 4
                        ),
                        "included": bool(float(percentages[index]) > 0.001),
                    }
                    for index in range(len(names))
                ],
                "nutrient_achievement": {
                    name: {
                        "achieved": round(float(nutrient_values[index]), 4),
                        "required": round(float(nutrient_targets[index]), 4),
                    }
                    for index, name in enumerate(self.nutrient_fields)
                },
                "summary": {
                    "total_ingredient_percentage": round(
                        float(sum(result.x) * 100), 6
                    ),
                    "active_ingredients_count": int(
                        sum(1 for value in percentages if float(value) > 0.001)
                    ),
                    "cost_per_kg": round(float(result.fun), 4),
                    "formulation_feasible": True,
                },
            }
        )
        return response

    @staticmethod
    def _base_response(
        request: FeedFormulationRequest | FeedFormulationV3Request,
    ) -> dict:
        return {
            "formulation_inputs": {
                "total_ingredients": len(request.ingredients),
                "ingredients": [
                    {
                        "name": ingredient.name,
                        "cost_per_kg": ingredient.cost_per_kg,
                        "min_percentage": ingredient.min_percentage * 100,
                        "max_percentage": ingredient.max_percentage * 100,
                    }
                    for ingredient in request.ingredients
                ],
                "nutrient_targets": request.nutrient_requirements.model_dump(),
            }
        }
