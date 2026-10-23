from worker.tasks import investigate_run


if __name__ == "__main__":
    job = investigate_run.delay("RUN-1042")

    print("Investigation submitted.")
    print("Task ID:", job.id)