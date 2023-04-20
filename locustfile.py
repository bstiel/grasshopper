import time
import datetime
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
        t0 = datetime.datetime.utcnow()
        try:
            async_result = self.client.send_task(name, args=args, kwargs=kwargs)
            result = async_result.get(self.task_timeout)  # blocking
            request_meta["response"] = result
            t1 = async_result.date_done
        except Exception as e:
            t1 = None
            request_meta["exception"] = e

        request_meta["response_time"] = None if not t1 else (t1 - t0).total_seconds() * 1000
        self._request_event.fire(**request_meta)  # this is what makes the request actually get logged in Locust
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
    def test_request1(self):
        self.client.send_task("request1")

    # @task
    # def test_request2(self):
    #     self.client.send_task("request2")
