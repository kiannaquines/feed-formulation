from types import SimpleNamespace

from schema.feed_v4 import FeedFormulationV4Request
from services.feed_optimization_service import FeedOptimizationService
from services.feed_optimization_v2_service import FeedOptimizationV2Service


class _NutrientTargets(SimpleNamespace):
    def model_dump(self) -> dict[str, float]:
        return vars(self)


class FeedOptimizationV4Service:
    def formulate(self, request: FeedFormulationV4Request) -> dict:
        nutrient_fields = tuple(request.nutrient_requirements)
        primary_solver = FeedOptimizationService()
        primary_solver.nutrient_fields = nutrient_fields
        adapted_request = SimpleNamespace(
            ingredients=[
                SimpleNamespace(
                    name=ingredient.name,
                    cost_per_kg=ingredient.cost_per_kg,
                    min_percentage=ingredient.min_percentage,
                    max_percentage=ingredient.max_percentage,
                    **{
                        name: ingredient.nutrients[name]
                        for name in nutrient_fields
                    },
                )
                for ingredient in request.ingredients
            ],
            nutrient_requirements=_NutrientTargets(**request.nutrient_requirements),
            optimization_method=request.optimization_method,
        )
        return FeedOptimizationV2Service(primary_solver).formulate(adapted_request)
