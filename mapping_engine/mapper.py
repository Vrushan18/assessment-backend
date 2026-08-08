from mapping_engine.schemas import MappedContext
from mapping_engine.rules import (
    L1_RULE,
    L2_ENGINEERING_SCIENCE,
    L2_COMMERCE_ARTS,
    L3_RULE,
    L4_RULE,
)


class ContextMapper:
    def map(self, context):

        level = context.certification_level.value
        domain = context.domain.value
        bloom = context.bloom_target.value

        if level == "L1":
            rule = L1_RULE

        elif level == "L2":
            if domain in ["Engineering", "Science"]:
                rule = L2_ENGINEERING_SCIENCE
            else:
                rule = L2_COMMERCE_ARTS

        elif level == "L3":
            rule = L3_RULE

        elif level == "L4":
            rule = L4_RULE

        else:
            raise ValueError(f"Unsupported certification level: {level}")

        bloom_distribution = {
            "Remember": 0,
            "Understand": 0,
            "Apply": 0,
            "Analyse": 0,
            "Evaluate": 0,
            "Create": 0,
        }

        bloom_distribution[bloom] = rule["question_count"]

        return MappedContext(
            pathway_id=f"{domain}_{level}",
            c_weights=rule["weights"],
            question_count_target=rule["question_count"],
            difficulty_distribution=rule["difficulty"],
            bloom_distribution=bloom_distribution,
            scenario_tags=[
                domain.lower(),
                level.lower(),
                bloom.lower()
            ]
        )