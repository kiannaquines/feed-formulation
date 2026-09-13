from schema.feed_v3 import NutrientsV3
from services.feed_optimization_service import FeedOptimizationService
from services.feed_optimization_v2_service import FeedOptimizationV2Service


class FeedOptimizationV3PrimaryService(FeedOptimizationService):
    nutrient_fields = tuple(NutrientsV3.model_fields)


class FeedOptimizationV3Service(FeedOptimizationV2Service):
    def __init__(self):
        super().__init__(primary_solver=FeedOptimizationV3PrimaryService())
