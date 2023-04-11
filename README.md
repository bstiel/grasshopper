## Locust Celery Client

Locust is an easy to use, scriptable and scalable performance testing tool.

To get started with Locust, head over to the Locust [documentation](http://docs.locust.io/en/stable/installation.html) and the Locust [Github repository](https://github.com/locustio/locust)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Define your Celery load tests in `locustfile.py`.

Inherit from `CeleryUser` which provides access to the Celery client via `self.client`.

Invoke you Celery task via `send_task(name, [optional] args, [optional] kwargs)`.

```python
class CeleryTask(CeleryUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def test_celery_task(self):
        self.client.send_task("celery_task", args=[1, 2, 3], kwargs={"key1": "value1"})
```


## Run load tests

Locust requires access to your Celery message broker (`host`) and result backend (`backend`), make sure to run Celery with a result backend.

Start locust passing the `--host` and `--backend` arguments on the command line (or the web ui):

```bash
locust --host=redis://localhost:6379/0 --backend=redis://localhost:6379/1
```

Head over to your browser http://localhost:8089 to run your load tests.