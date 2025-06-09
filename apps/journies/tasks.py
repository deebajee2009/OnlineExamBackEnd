# journies/tasks.py
from celery import shared_task
from django.utils import timezone
from apps.journies.models import JourneyTemplate
from apps.journies.group_exam_result import calculate_group_exam_result

@shared_task
def process_journey_template(template_id):
    """
    This will fire at template.scheduled_time.
    """
    print(f"[task] process_journey_template({template_id}) @ {timezone.now()}", flush=True)
    # try:
    #     jt = JourneyTemplate.objects.get(pk=template_id)
    # except JourneyTemplate.DoesNotExist:
    #     return
    # Journey.objects.filter(journey_id=journey_id)
    # Your “when time arrives” logic here:
    # now = timezone.now()
    # e.g. mark the journey as started, send notifications, etc.
    # jt.result_operation_status = 'started'
    # jt.save(update_fields=['result_operation_status'])
    # operation_succuss = calculate_group_exam_result(template_id)
    try:
        success = calculate_group_exam_result(template_id)
        print(f"[task] calculate_group_exam_result → {success}", flush=True)
        return success
    except Exception as exc:
        print(f"[task][ERROR] {exc!r}", flush=True)
        raise  # re-raise so Celery marks the task failed
    # if operation_succuss:
    #     jt.result_operation_status = 'done'
    #     jt.save(update_fields=['result_operation_status'])
    # else:
    #     jt.result_operation_status = 'failed'
    #     jt.save(update_fields=['result_operation_status'])
