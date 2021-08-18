from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type

from notifier.types import (
    CachedUserConfig,
    GlobalOverridesConfig,
    NewPostsInfo,
    RawPost,
    RawUserConfig,
    Subscription,
    SupportedWikiConfig,
)


def try_cache(
    *,
    get: Callable,
    store: Callable,
    do_not_store: Any = None,
    catch: Tuple[Type[Exception], ...] = None,
) -> None:
    """Attempts to retrieve data from somewhere. If it succeeds, caches the
    data. If it fails, does nothing.

    Intended usage is for the data to be subsequently retrieved from the
    cache. This ensure that valid data is always received, even if the
    original call failed - in this case, old cached data is used instead.

    If it is necessary for the getter to succeed (e.g. for permanent
    storage of new posts), this function should not be used. It should only
    be used when failure is possible and acceptable (e.g. for temporary
    storage of user config).

    :param get: Callable that takes no argument that retrieves data, and
    may fail.

    :param store: Callable that takes the result of `get` as its only
    argument and caches the data.

    :param do_not_store: If the result of `get` is equal to this,
    it will not be stored. Defaults to None. If `get` returning None is
    desirable, set to a sentinel value.

    :param catch: Tuple of exceptions to catch. If `get` emits any other
    kind of error, it will not be caught. Defaults to catching no
    exceptions which obviously is not recommended. If an exception is
    caught, the store is not called.

    Functions intended to be used with this function typically either raise
    an error or return a no-op value, so `do_not_store` and `catch` should
    rarely be used together.
    """
    if catch is None:
        catch = tuple()
    value = do_not_store
    try:
        value = get()
    except catch as error:
        print(f"{get.__name__} failed; will use value from cache")
        print(f"Failure: {error}")
    if value != do_not_store:
        store(value)


class BaseDatabaseDriver(ABC):
    """Base structure for the database driver which must be fulfilled by
    any implementations."""

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def create_tables(self) -> None:
        """Initial setup for the database."""

    @abstractmethod
    def store_global_overrides(
        self, global_overrides: GlobalOverridesConfig
    ) -> None:
        """Store all global overrides, overwriting any that are already
        present."""

    @abstractmethod
    def get_global_overrides(self) -> GlobalOverridesConfig:
        """Gets all global overrides, keyed to the ID of the wiki they are
        set for."""

    @abstractmethod
    def find_new_threads(self, thread_ids: Iterable[str]) -> List[str]:
        """From a list of thread IDs, return those that are not already
        present in the cache."""

    @abstractmethod
    def get_new_posts_for_user(
        self, user_id: str, timestamp_range: Tuple[int, int]
    ) -> NewPostsInfo:
        """Get new posts for the users with the given ID made during the
        given time range.

        Returns a dict containing the thread posts and the post replies.
        """

    @abstractmethod
    def get_user_configs(self, frequency: str) -> List[CachedUserConfig]:
        """Get the cached config for users subscribed to the given channel
        frequency.

        The cached config does not contain subscriptions, but does contain
        the timestamp at which the user was last notified.
        """

    @abstractmethod
    def store_user_configs(self, user_configs: List[RawUserConfig]) -> None:
        """Caches user notification configurations.

        :param user_configs: List of configurations for all users.
        """

    @abstractmethod
    def check_would_email(self, frequencies: List[str]) -> bool:
        """Checks if there is at least one user who is subscribed to one of
        the provided frequency channels who has opted to recieve
        notifications via email.

        :param frequencies: The list of frequency channel names.
        """

    @abstractmethod
    def store_manual_sub(
        self, user_id: str, subscription: Subscription
    ) -> None:
        """Caches a single user subscription configuration.

        :param user_id: The numeric Wikidot ID of the user, as text.
        :param thread_id: Data for the subscription.
        """

    @abstractmethod
    def store_user_last_notified(
        self, user_id: str, last_notified_timestamp: int
    ) -> None:
        """Store the time at which the user with the given ID was last
        notified.

        The time should be the time of the most recent post the user has
        been notified about, but must only be saved once the notification
        has actually been delivered.
        """

    @abstractmethod
    def get_supported_wikis(self) -> List[SupportedWikiConfig]:
        """Get a list of supported wikis."""

    @abstractmethod
    def store_supported_wikis(self, wikis: List[SupportedWikiConfig]) -> None:
        """Stores a set of supported wikis in the database, overwriting any
        that are already present."""

    @abstractmethod
    def store_thread(
        self,
        wiki_id: str,
        category: Tuple[str, str],
        thread: Tuple[str, str, Optional[str], int],
    ) -> None:
        """Store a thread. Doesn't matter if the thread or category is
        already known or not.

        :param wiki_id: The ID of the wiki that contains the thread.
        :param thread: A tuple containing information about the thread: ID,
        title, creator username, and created timestamp.
        :param category: A tuple containing the ID and name of the category.
        """

    @abstractmethod
    def store_post(self, post: RawPost) -> None:
        """Store a post."""


class DatabaseWithSqlFileCache(BaseDatabaseDriver, ABC):
    """Utilities for a database to read its SQL commands directly from the
    filesystem, caching those commands between batches of queries.

    This is so that the SQL commands can be safely edited between queries
    with no downtime.

    Execute clear_query_file_cache to clear the cache and force the next
    call to each query to re-read from the filesystem.
    """

    builtin_queries_dir = Path(__file__).parent.parent / "queries"

    def __init__(self):
        super().__init__()
        self.clear_query_file_cache()

    def clear_query_file_cache(self):
        """Clears the cache of query files, causing subsequent calls to
        them to re-read the query from the filesystem."""
        self.query_cache = {}

    def read_query_file(self, query_name: str) -> None:
        """Reads the contents of a query file from the filesystem and
        caches it."""
        try:
            query_path = next(
                path
                for path in self.builtin_queries_dir.iterdir()
                if path.name.split(".")[0] == query_name
            )
        except StopIteration as stop:
            raise ValueError(f"Query {query_name} does not exist") from stop
        with query_path.open() as file:
            query = file.read()
        self.query_cache[query_name] = {
            "script": query_path.name.endswith(".script.sql"),
            "query": query,
        }

    def cache_named_query(self, query_name: str) -> None:
        """Reads an SQL query from the source and puts it to the cache,
        unless it is already present.

        :param query_name: The name of the query to execute, which must
        have a corresponding SQL file.
        """
        if query_name not in self.query_cache:
            self.read_query_file(query_name)