from typing import Dict, List, Literal, Optional, TypedDict, Union

IsSecure = Union[Literal[0], Literal[1]]


class WikidotResponse(TypedDict):
    """A module response from Wikidot."""

    status: str
    body: str
    message: Optional[str]


class LocalConfigPaths(TypedDict):
    """Segment of the local config file containing paths."""

    lang: str


class DatabaseConfig(TypedDict):
    """Configuration for the database."""

    driver: str
    database_name: str


class LocalConfig(TypedDict):
    """Contents of the local config file."""

    wikidot_username: str
    config_wiki: str
    user_config_category: str
    wiki_config_category: str
    overrides_url: str
    gmail_username: str
    database: DatabaseConfig
    path: LocalConfigPaths


class SupportedWikiConfig(TypedDict):
    """A single remote wiki config."""

    id: str
    name: str
    secure: IsSecure


class AuthConfig(TypedDict):
    """Contents of the authentication config file, after processing."""

    wikidot_password: str
    gmail_password: str
    mysql_host: str
    mysql_username: str
    mysql_password: str


GlobalOverrideAction = Union[Literal["mute"], Literal["mute_thread"]]


class GlobalOverrideConfig(TypedDict, total=False):
    """A single remote override config."""

    action: GlobalOverrideAction
    category_id_is: Optional[str]
    thread_id_is: Optional[str]
    thread_title_matches: Optional[str]


# A collection of remote override configs, keyed by wiki.
GlobalOverridesConfig = Dict[str, List[GlobalOverrideConfig]]

# Direction of a subscription (-1 indicates an unsubscription).
SubscriptionCardinality = Union[Literal[-1], Literal[1]]


class Subscription(TypedDict):
    """A user's (un)subscription to a single thread or post."""

    thread_id: str
    post_id: Optional[str]
    sub: SubscriptionCardinality


# A user's choice of delivery method
DeliveryMethod = Union[Literal["pm"], Literal["email"]]


class RawUserConfig(TypedDict):
    """A single remote user config."""

    user_id: str
    username: str
    frequency: str
    language: str
    delivery: DeliveryMethod
    user_base_notified: int
    subscriptions: List[Subscription]
    unsubscriptions: List[Subscription]


class CachedUserConfig(TypedDict):
    """A single remote user config as retrieved from the database."""

    user_id: str
    username: str
    frequency: str
    language: str
    delivery: DeliveryMethod
    last_notified_timestamp: int
    manual_subs: List[Subscription]
    auto_subs: List[Subscription]


class RawThreadMeta(TypedDict):
    """Information about a thread from its header."""

    category_id: Optional[str]
    category_name: Optional[str]
    title: str
    creator_username: Optional[str]
    created_timestamp: int
    page_count: int


class ThreadInfo(TypedDict):
    """Information about a thread to be stored in the database."""

    id: str
    title: str
    wiki_id: str
    category_id: Optional[str]
    category_name: Optional[str]
    creator_username: Optional[str]
    created_timestamp: int


class RawPost(TypedDict):
    """Information for a single post from remote."""

    id: str
    thread_id: str
    parent_post_id: Optional[str]
    posted_timestamp: int
    title: str
    snippet: str
    user_id: str
    username: str


class PostInfo(TypedDict):
    """Information for a single post returned from the cache."""

    id: str
    title: str
    username: str
    posted_timestamp: int
    snippet: str
    thread_id: str
    thread_title: str
    thread_creator: Optional[str]
    thread_timestamp: int
    wiki_id: str
    wiki_name: str
    wiki_secure: IsSecure
    category_id: Optional[str]
    category_name: Optional[str]


class ThreadPostInfo(PostInfo):
    """Information for a new post made to a thread from the cache."""


class PostReplyInfo(PostInfo):
    """Information for a new reply to a post from the cache."""

    parent_post_id: str
    parent_title: str
    parent_username: str
    parent_posted_timestamp: int


class NewPostsInfo(TypedDict):
    """All new posts returned from the cache."""

    thread_posts: List[ThreadPostInfo]
    post_replies: List[PostReplyInfo]


# Email addresses keyed by Wikidot usernames.
EmailAddresses = Dict[str, str]
