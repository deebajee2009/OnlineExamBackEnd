from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from celery.result import AsyncResult
from datetime import timedelta

from .models import JourneyTemplate
from .tasks import process_journey_template

@receiver(post_save, sender=JourneyTemplate)
def schedule_journey_task(sender, instance, **kwargs):
    """
    Whenever a JourneyTemplate is created or updated:
      • Compute its “scheduled_time” (start_datetime + time_minutes_limit).
      • If that time is in the future:
          – Cancel any previously queued task for this instance.
          – Enqueue a fresh Celery task to fire at the new time.
          – Store the new task’s ID back on the model (via update()).
    """
    # ────────────────────────────────────────────────────────────────────────
    # A) Calculate when the task should actually run:
    if instance.start_datetime and instance.time_minutes_limit:
        sched = (
            instance.start_datetime
            + timedelta(minutes=instance.time_minutes_limit)
            + timedelta(seconds=5)
        )
        print(f"→ sched={sched}  now={timezone.now()}", flush=True)
    else:
        sched = None
    # ────────────────────────────────────────────────────────────────────────
    # B) Only proceed if that scheduled_time exists and lies in the future:
    print(f"→ sched={sched}  now={timezone.now()}", flush=True)
    if not sched or sched <= timezone.now():
        return

    # ────────────────────────────────────────────────────────────────────────
    # # C) Revoke (cancel) the previous pending task, if any:
    # if instance.celery_task_id:
    #     AsyncResult(instance.celery_task_id).revoke()

    # ────────────────────────────────────────────────────────────────────────
    # D) Schedule the new one-time task at exactly `sched`:
    print('okay we are at here to trigger apply async')
    result = process_journey_template.apply_async(
        args=(instance.id,),
        eta=sched
    )

    # ────────────────────────────────────────────────────────────────────────
    # E) Update the model with the new task ID:
    # JourneyTemplate.objects.filter(pk=instance.pk).update(
    #     scheduled_time=sched,
    #     celery_task_id=result.id
    # )
