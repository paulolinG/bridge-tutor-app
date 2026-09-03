from app.models.rubric import RubricScore


def _score(**overrides: int) -> RubricScore:
    defaults = dict(
        subject_knowledge=15,
        subject_knowledge_rationale="ok",
        instructional_quality=30,
        instructional_quality_rationale="ok",
        pedagogical_adaptability=15,
        pedagogical_adaptability_rationale="ok",
        organization=15,
        organization_rationale="ok",
    )
    defaults.update(overrides)
    return RubricScore(**defaults)


def test_total_score_sums_all_categories() -> None:
    score = _score()
    assert score.total_score == 15 + 30 + 15 + 15


def test_passed_true_at_exactly_70() -> None:
    score = _score(
        subject_knowledge=10,
        instructional_quality=30,
        pedagogical_adaptability=15,
        organization=15,
    )
    assert score.total_score == 70
    assert score.passed is True


def test_passed_false_below_70() -> None:
    score = _score(
        subject_knowledge=10,
        instructional_quality=29,
        pedagogical_adaptability=15,
        organization=15,
    )
    assert score.total_score == 69
    assert score.passed is False


def test_computed_fields_excluded_from_input_schema() -> None:
    schema = RubricScore.model_json_schema()
    assert "total_score" not in schema["properties"]
    assert "passed" not in schema["properties"]
