import random
from apps.questions.models import Question
from apps.journies.models import Journey, JourneyStep


def get_next_journey_step(journey_id, current_journey_step_id=None):

    journey = Journey.objects.get(journey_id=journey_id)
    if not journey.is_active():
        return None

    if journey.journey_static:
        qs = JourneyStep.objects.filter(journey=journey)
        if current_journey_step_id is not None:
            try:
                # next_journey_step = JourneyStep.objects.get(
                #     journey=journey,
                #     journey_step_id__gt=current_journey_step_id
                # )
                qs = qs.filter(step_id__gt=current_journey_step_id)

            except JourneyStep.DoesNotExist:
                return None
        next_journey_step = qs.order_by('step_id').first()
        return next_journey_step  # will be None if no more steps

    available_ids = list(
        Question.objects.filter(
            is_active=True
        ).exclude(
            id__in=journey.steps.values_list('question_id', flat=True)
        ).values_list('id', flat=True)
    )

    if available_ids:
        journey_step = JourneyStep.objects.create(
            journey=journey,
            question=Question.objects.get(id=random.choice(available_ids))
        )
        return journey_step
    return None
