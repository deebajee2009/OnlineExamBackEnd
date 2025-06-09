import polars as pl
from django.db import transaction
from django.db.models import Count, Q
from apps.journies.models import Journey, JourneyStepTemplate, JourneyStep, UserAnswer, StaticJourneyType

def calculate_group_exam_result(journey_template_id):
    """
    For the given JourneyTemplate (exam):
     - Count each participant's answers (correct, wrong, unanswered)
     - Compute score = (correct - wrong/3) / total_questions * 100
     - Assign a dense rank by score (highest first)
     - Persist all of that back into each Journey row:
         answered_count, unanswered_count, correct_count,
         wrong_count, rank, total_participants
    Returns True on success, False on any error.
    """
    print(f'journey_template_id is {journey_template_id}', flush=True )
    try:
        # 1) Total number of questions in the exam
        total_questions = JourneyStepTemplate.objects.filter(
            journey_template_id=journey_template_id
        ).count()
        print(f'total questions is {total_questions}', flush=True )
        if total_questions == 0:
            return False

        # 2) Fetch all Journeys for this template and annotate raw counts
        # journeys_qs = (
        #     Journey.objects
        #     .filter(journey_static_id=journey_template_id, journey_type=StaticJourneyType.GROUP_EXAM)
        #     .select_related('user')
        #     .annotate(
        #         correct_count = Count('steps', filter=Q(steps__answer_result=UserAnswer.CORRECT)),
        #         wrong_count   = Count('steps', filter=Q(steps__answer_result=UserAnswer.FALSE)),
        #         unanswered_count = Count('steps', filter=Q(steps__answer_result=UserAnswer.NOT_SELECTED)),
        #     )
        # )

        journeys_qs = (
            Journey.objects
                   .filter(
                       journey_static_id=journey_template_id,
                       journey_type=StaticJourneyType.GROUP_EXAM,
                   )
                   .select_related('user')
                   .annotate(
                       annotated_correct   = Count(
                           'steps',
                           filter=Q(steps__answer_result=UserAnswer.CORRECT)
                       ),
                       annotated_wrong     = Count(
                           'steps',
                           filter=Q(steps__answer_result=UserAnswer.FALSE)
                       ),
                       annotated_unanswered= Count(
                           'steps',
                           filter=Q(steps__answer_result=UserAnswer.NOT_SELECTED)
                       ),
                   )
        )
        print('journey_qs passed ', flush=True)
        actual_journeys = list(journeys_qs)
        total_participants = len(set(j.user_id for j in actual_journeys))
        # total_participants = journeys_qs.count()
        # total_participants = (
        #     journeys_qs
        #     .values('user_id')
        #     .distinct()
        #     .count()
        # )
        print(f'total participant is {total_participants}', flush=True )
        # 3) Build a Polars DataFrame
        records = []
        for j in journeys_qs:

            records.append({
                'journey_id'      : j.journey_id,
                'correct_count'   : j.annotated_correct,
                'wrong_count'     : j.annotated_wrong,
                'unanswered_count': total_questions - (j.annotated_correct + j.annotated_wrong),
            })
        print('passed appending wrong right and unanswered', flush=True)
        print(f'records {records}', flush=True)
        # df = pl.DataFrame(records)
        #
        # # 4) Compute score and dense rank
        # df = df.with_columns([
        #     (
        #         (pl.col('correct_count') - pl.col('wrong_count') / 3.0)
        #         / total_questions * 100
        #     ).round(2).alias('score')
        # ])
        # df = df.sort('score', reverse=True)
        # df = df.with_columns(
        #     pl.col('score')
        #     .rank(method='dense', reverse=True)
        #     .cast(pl.UInt32)
        #     .alias('rank')
        # )
        # print(df.head(5), flush=True)
        #
        # # 5) Persist back into Journey rows
        # journeys_to_update = []
        # # Build a mapping from journey_id -> (score_row, rank, counts)
        # for row in df.iter_rows(named=True):
        #     jid = row['journey_id']
        #     j = Journey.objects.get(journey_id=jid)
        #     # answered_count = correct + wrong
        #     answered = row['correct_count'] + row['wrong_count']
        #
        #     j.correct_count      = row['correct_count']
        #     j.wrong_count        = row['wrong_count']
        #     j.unanswered_count   = total_questions - answered
        #     j.answered_count     = answered
        #     j.rank               = int(row['rank'])
        #     j.score              = row['score']
        #     j.total_participants = total_participants
        #     # (If you had a score field on Journey, you'd set j.score = row['score'])
        #     journeys_to_update.append(j)

        df = pl.DataFrame(records)
        print(df.head(5), flush=True)

        # 4) Compute score and dense rank
        df = df.with_columns([
            (
                (pl.col('correct_count') - pl.col('wrong_count') / 3.0)
                / total_questions * 100
            ).round(2).alias('score')
        ])

        print(df.head(5), flush=True)

        df = df.sort('score', descending=True)
        print(df.head(5), flush=True)
        df = df.with_columns(
            pl.col('score')
              .rank(method='dense', descending=True)
              .cast(pl.UInt32)
              .alias('rank')
        )
        print(df.head(5), flush=True)

        # 5) Persist back into Journey rows
        journeys_to_update = []

        # Uniform handling for all rows (even if it's just one)
        for row in df.iter_rows(named=True):
            jid = row['journey_id']
            j = Journey.objects.get(journey_id=jid)
            answered = row['correct_count'] + row['wrong_count']

            j.correct_count      = row['correct_count']
            j.wrong_count        = row['wrong_count']
            j.unanswered_count   = total_questions - answered
            j.answered_count     = answered
            j.rank               = int(row['rank'])
            j.score              = row['score']
            j.total_participants = total_participants
            journeys_to_update.append(j)


        with transaction.atomic():
            Journey.objects.bulk_update(
                journeys_to_update,
                [
                    'answered_count',
                    'unanswered_count',
                    'correct_count',
                    'wrong_count',
                    'rank',
                    'score',
                    'total_participants'
                ]
            )

        return True

    except Exception as exc:
        print(f"An error occurred: {exc}", flush=True)
        import traceback
        traceback.print_exc()
        return False
