"""Single source of truth for externally side-effecting provider capabilities."""

SOCIAL_POST_PLATFORMS = frozenset({
    "facebook", "instagram", "youtube", "tiktok", "linkedin", "x",
})

SUPPORTED_PROVIDER_ACTIONS = frozenset({
    ("gmail", "send_message"),
    ("outlook", "send_message"),
    ("x", "create_post"),
    ("linkedin", "create_post"),
})

SIDE_EFFECT_ACTIONS = frozenset({
    "send_message", "send_email", "create_post", "schedule_post", "comment",
    "reply", "like", "reaction", "share", "follow", "unfollow",
    "friend_request", "live", "call",
})


def is_supported_provider_action(platform: str, action: str) -> bool:
    return (platform.lower().strip(), action.lower().strip()) in SUPPORTED_PROVIDER_ACTIONS


def requires_human_approval(action: str) -> bool:
    return action.lower().strip() in SIDE_EFFECT_ACTIONS
