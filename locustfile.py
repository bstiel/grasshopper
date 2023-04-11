import time
from celery import Celery
from locust import User, between, task, events


@events.init_command_line_parser.add_listener
def _(parser):
    """
    Additional command line/ui argument for Celery backend url.
    """
    parser.add_argument("--backend", type=str, env_var="LOCUST_CELERY_BACKEND", default="", required=True, include_in_web_ui=True, help="Celery backend url")



class CeleryClient:
    """
    CeleryClient is a wrapper around the Celery client.
    It proxies any function calls and fires the *request* event when they finish,
    so that the calls get recorded in Locust.
    """

    def __init__(self, broker, backend, task_timeout, request_event):
        self.client = Celery(broker=broker, backend=backend)
        self.task_timeout = task_timeout
        self._request_event = request_event

    def send_task(self, name, args=None, kwargs=None):
        request_meta = {
            "request_type": "celery",
            "response_length": 0,
            "name": name,
            "start_time": time.time(),
            "response": None,
            "context": {},
            "exception": None,
        }
        start_perf_counter = time.perf_counter()
        try:
            task = self.client.send_task(name, args=args, kwargs=kwargs)
            t0 = time.time()
            while self.client.AsyncResult(task.id).status == "PENDING":
                t1 = time.time()
                if self.task_timeout is not None and (t1 - t0) > self.task_timeout:
                    raise ValueError(f"Celery soft task timeout [{name}]: no response after {round(t1 - t0, 1)}s")
                time.sleep(0.05)
            task = self.client.AsyncResult(task.id)
            if task.status == "SUCCESS":
                request_meta["response"] = task.get()
            else:
                request_meta["exception"] = task.status
        except Exception as e:
            request_meta["exception"] = e
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self._request_event.fire(**request_meta)  # This is what makes the request actually get logged in Locust
        return request_meta["response"]


class CeleryUser(User):

    abstract = True  # do not instantiate this as an actual user when running Locust

    def __init__(self, environment):
        super().__init__(environment)
        self.client = CeleryClient(
            broker=environment.host,
            backend=environment.parsed_options.backend,
            task_timeout=environment.stop_timeout,
            request_event=environment.events.request)


class CeleryTask(CeleryUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def test_celery_task(self):
        self.client.send_task("celery_task_name", args=[1, 2, 3], kwargs={"key1": "value1"})
