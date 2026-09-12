import asyncio as aio
import typing as t

T = t.TypeVar("T")


async def _awaitable_raise_return_exc_distinguishable_wrapper(awaitable: t.Awaitable[T]) -> tuple[T] | Exception:
	"""Return either the exception raised, or the value returned by awaitable wrapped in a 1-tuple, to distinguish between an exception returned and an exception raised."""

	try:
		return (await awaitable,)
	except Exception as e:
		return e


async def gather(*awaitables: t.Awaitable[T], exc_group_msg: str) -> list[T]:
	"""Gather all awaitables using `asyncio.gather()`, furthermore if any exception is raised out of any of the awaitables, raise an ExceptionGroup containing exceptions of all awaitables that raised one.

	Args:
		awaitables: The awaitables to gather.
		exc_group_msg: The message to use for the ExceptionGroup if any of the awaitables raise an exception.

	Returns:
		A list of all values returned by the awaitables, in the same order as the awaitables were passed in.

	Raises:
		ExceptionGroup: If any of the awaitables raised an exception, an ExceptionGroup will be raised containing all exceptions raised by the awaitables.
	"""

	awaitables_wrapped = (_awaitable_raise_return_exc_distinguishable_wrapper(awaitable) for awaitable in awaitables)

	results = await aio.gather(*awaitables_wrapped)

	exceptions: list[Exception] = []
	values: list[T] = []

	for result in results:
		if isinstance(result, tuple):
			if not exceptions:  # dont bother filling the values anymore if we're going to raise later anyway
				(unwrapped,) = result
				values.append(unwrapped)
		else:
			exceptions.append(result)

	if exceptions:
		raise ExceptionGroup(exc_group_msg, exceptions)

	return values
