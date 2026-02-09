from celery import shared_task


@shared_task
def upload_order_task(visit_id):
    pass


@shared_task
def retrieve_results_task():
    pass
