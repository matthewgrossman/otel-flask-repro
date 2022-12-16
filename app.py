from gevent import monkey
monkey.patch_all()

import flask
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.flask import FlaskInstrumentor, _ENVIRON_ACTIVATION_KEY
import gevent
import contextvars

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
FlaskInstrumentor().instrument()
app = flask.Flask(__name__)

@app.route('/test', methods=['GET'])
def test_route():
    fn = wrap_fn_in_req_context__broken(func_that_accesses_req_context)
    # fn = wrap_fn_in_req_context__workaround(func_that_accesses_req_context)

    # Create a new greenlet that runs our wrapped func.
    # Inherit the current `contextvar` ctx, as recommended by greenlet docs:
    # https://greenlet.readthedocs.io/en/stable/contextvars.html
    greenlet = gevent.spawn(fn)
    greenlet.gr_context = contextvars.copy_context()

    return {
        'header': greenlet.get()
    }


def wrap_fn_in_req_context__broken(fn):
    # this is the flask-docs recommended way to pass req context to a greenlet
    # https://flask.palletsprojects.com/en/2.2.x/api/#flask.copy_current_request_context
    fn = flask.copy_current_request_context(fn)
    return fn


def wrap_fn_in_req_context__workaround(fn):
    # create a copy of the environ,
    # pop off the flask-instrumentor's sentinel key,
    # and then create a new flask request context

    new_environ = flask.request.environ.copy()
    new_environ.pop(_ENVIRON_ACTIVATION_KEY, None)
    new_req_ctx = flask.current_app.request_context(new_environ)

    def wrapper(*args, **kwargs):
        with new_req_ctx:
            return fn(*args, **kwargs)

    return wrapper


def func_that_accesses_req_context() -> str:
    # example function that *might* run within a greenlet,
    # and therefore should be wrapped with a request context
    # prior to running
    with tracer.start_as_current_span("span_in_greenlet"):
        return flask.request.headers.get("x-test-header", "no header")
