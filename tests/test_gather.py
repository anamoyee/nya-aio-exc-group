import asyncio

import pytest

import nya_aio_exc_group

# --- Helper Awaitables ---


async def success_task(val):
	await asyncio.sleep(0.01)
	return val


async def fail_task(exc: Exception):
	await asyncio.sleep(0.01)
	raise exc


async def return_exc_task(exc: Exception):
	await asyncio.sleep(0.01)
	return exc


# --- Unit Tests ---


@pytest.mark.asyncio
async def test_gather_all_successful():
	"""Test standard execution where all awaitables return values."""
	results = await nya_aio_exc_group.gather(success_task(1), success_task(2), success_task(3), exc_group_msg="Failed")
	assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_gather_empty_awaitables():
	"""Test gathering with no awaitables passed."""
	results = await nya_aio_exc_group.gather(exc_group_msg="Failed")
	assert results == []


@pytest.mark.asyncio
async def test_gather_single_exception_raises_exception_group():
	"""Test that a single failure still raises an ExceptionGroup (not a raw exception)."""
	with pytest.raises(ExceptionGroup) as exc_info:
		await nya_aio_exc_group.gather(success_task("ok"), fail_task(ValueError("single error")), exc_group_msg="Single Failure Group")

	eg = exc_info.value
	assert eg.message == "Single Failure Group"
	assert len(eg.exceptions) == 1
	assert isinstance(eg.exceptions[0], ValueError)
	assert str(eg.exceptions[0]) == "single error"


@pytest.mark.asyncio
async def test_gather_multiple_exceptions_collected():
	"""Test that all exceptions are gathered even if tasks complete at different times."""
	with pytest.raises(ExceptionGroup) as exc_info:
		await nya_aio_exc_group.gather(
			fail_task(ValueError("first failure")), success_task("ok"), fail_task(TypeError("second failure")), exc_group_msg="Multiple Failures"
		)

	eg = exc_info.value
	assert eg.message == "Multiple Failures"
	assert len(eg.exceptions) == 2
	assert isinstance(eg.exceptions[0], ValueError)
	assert isinstance(eg.exceptions[1], TypeError)


@pytest.mark.asyncio
async def test_distinguish_returned_exception_vs_raised_exception():
	"""Test that an Exception returned as a value is not treated as a raised error."""
	returned_err = ValueError("I am a return value")

	# Should succeed because the exception is returned, not raised
	results = await nya_aio_exc_group.gather(success_task(100), return_exc_task(returned_err), exc_group_msg="Should not raise")

	assert results == [100, returned_err]
	assert results[1] is returned_err


@pytest.mark.asyncio
async def test_returned_exception_with_a_raised_exception():
	"""Test that when one task raises an error and another returns an Exception object, only the raised exception ends up in the ExceptionGroup."""
	returned_err = RuntimeError("Returned error value")
	raised_err = KeyError("Raised error")

	with pytest.raises(ExceptionGroup) as exc_info:
		await nya_aio_exc_group.gather(return_exc_task(returned_err), fail_task(raised_err), exc_group_msg="Mixed Exception test")

	eg = exc_info.value
	assert len(eg.exceptions) == 1
	assert eg.exceptions[0] is raised_err


@pytest.mark.asyncio
async def test_exception_group_handling_with_except_star():
	"""Test catching the resulting ExceptionGroup using Python 3.11+ except* syntax."""
	handled = []

	try:
		await nya_aio_exc_group.gather(
			fail_task(ZeroDivisionError("div by zero")), fail_task(TypeError("invalid type")), exc_group_msg="Syntax check"
		)
	except* ZeroDivisionError as eg:
		handled.append(type(eg.exceptions[0]))
	except* TypeError as eg:
		handled.append(type(eg.exceptions[0]))

	assert ZeroDivisionError in handled
	assert TypeError in handled
