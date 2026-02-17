from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class WhatsAppConfig:
    enabled: bool = False
    bridge_url: str = "ws://localhost:3001"
    bridge_token: str = ""
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "bridge_url": self.bridge_url,
            "bridge_token": self.bridge_token,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WhatsAppConfig":
        return cls(
            enabled=data.get("enabled", False),
            bridge_url=data.get("bridge_url", "ws://localhost:3001"),
            bridge_token=data.get("bridge_token", ""),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "bridgeUrl": self.bridge_url,
            "bridgeToken": self.bridge_token,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "WhatsAppConfig":
        return cls(
            enabled=data.get("enabled", False),
            bridge_url=data.get("bridgeUrl", "ws://localhost:3001"),
            bridge_token=data.get("bridgeToken", ""),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class TelegramConfig:
    enabled: bool = False
    token: str = ""
    allow_from: List[str] = field(default_factory=list)
    proxy: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "token": self.token,
            "allow_from": self.allow_from,
            "proxy": self.proxy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelegramConfig":
        return cls(
            enabled=data.get("enabled", False),
            token=data.get("token", ""),
            allow_from=data.get("allow_from", []),
            proxy=data.get("proxy"),
        )

    def to_nanobot_config(self) -> dict:
        result = {
            "enabled": self.enabled,
            "token": self.token,
            "allowFrom": self.allow_from,
        }
        if self.proxy:
            result["proxy"] = self.proxy
        return result

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "TelegramConfig":
        return cls(
            enabled=data.get("enabled", False),
            token=data.get("token", ""),
            allow_from=data.get("allowFrom", []),
            proxy=data.get("proxy"),
        )


@dataclass
class DiscordConfig:
    enabled: bool = False
    token: str = ""
    allow_from: List[str] = field(default_factory=list)
    gateway_url: str = "wss://gateway.discord.gg/?v=10&encoding=json"
    intents: int = 37377

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "token": self.token,
            "allow_from": self.allow_from,
            "gateway_url": self.gateway_url,
            "intents": self.intents,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiscordConfig":
        return cls(
            enabled=data.get("enabled", False),
            token=data.get("token", ""),
            allow_from=data.get("allow_from", []),
            gateway_url=data.get("gateway_url", "wss://gateway.discord.gg/?v=10&encoding=json"),
            intents=data.get("intents", 37377),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "token": self.token,
            "allowFrom": self.allow_from,
            "gatewayUrl": self.gateway_url,
            "intents": self.intents,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "DiscordConfig":
        return cls(
            enabled=data.get("enabled", False),
            token=data.get("token", ""),
            allow_from=data.get("allowFrom", []),
            gateway_url=data.get("gatewayUrl", "wss://gateway.discord.gg/?v=10&encoding=json"),
            intents=data.get("intents", 37377),
        )


@dataclass
class FeishuConfig:
    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""
    encrypt_key: str = ""
    verification_token: str = ""
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "encrypt_key": self.encrypt_key,
            "verification_token": self.verification_token,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeishuConfig":
        return cls(
            enabled=data.get("enabled", False),
            app_id=data.get("app_id", ""),
            app_secret=data.get("app_secret", ""),
            encrypt_key=data.get("encrypt_key", ""),
            verification_token=data.get("verification_token", ""),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "appId": self.app_id,
            "appSecret": self.app_secret,
            "encryptKey": self.encrypt_key,
            "verificationToken": self.verification_token,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "FeishuConfig":
        return cls(
            enabled=data.get("enabled", False),
            app_id=data.get("appId", ""),
            app_secret=data.get("appSecret", ""),
            encrypt_key=data.get("encryptKey", ""),
            verification_token=data.get("verificationToken", ""),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class DingTalkConfig:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DingTalkConfig":
        return cls(
            enabled=data.get("enabled", False),
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "DingTalkConfig":
        return cls(
            enabled=data.get("enabled", False),
            client_id=data.get("clientId", ""),
            client_secret=data.get("clientSecret", ""),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class SlackDMConfig:
    enabled: bool = True
    policy: str = "open"
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "policy": self.policy,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlackDMConfig":
        return cls(
            enabled=data.get("enabled", True),
            policy=data.get("policy", "open"),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "policy": self.policy,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "SlackDMConfig":
        return cls(
            enabled=data.get("enabled", True),
            policy=data.get("policy", "open"),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class SlackConfig:
    enabled: bool = False
    mode: str = "socket"
    webhook_path: str = "/slack/events"
    bot_token: str = ""
    app_token: str = ""
    user_token_read_only: bool = True
    group_policy: str = "mention"
    group_allow_from: List[str] = field(default_factory=list)
    dm: SlackDMConfig = field(default_factory=SlackDMConfig)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "webhook_path": self.webhook_path,
            "bot_token": self.bot_token,
            "app_token": self.app_token,
            "user_token_read_only": self.user_token_read_only,
            "group_policy": self.group_policy,
            "group_allow_from": self.group_allow_from,
            "dm": self.dm.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlackConfig":
        dm_data = data.get("dm", {})
        return cls(
            enabled=data.get("enabled", False),
            mode=data.get("mode", "socket"),
            webhook_path=data.get("webhook_path", "/slack/events"),
            bot_token=data.get("bot_token", ""),
            app_token=data.get("app_token", ""),
            user_token_read_only=data.get("user_token_read_only", True),
            group_policy=data.get("group_policy", "mention"),
            group_allow_from=data.get("group_allow_from", []),
            dm=SlackDMConfig.from_dict(dm_data) if dm_data else SlackDMConfig(),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "webhookPath": self.webhook_path,
            "botToken": self.bot_token,
            "appToken": self.app_token,
            "userTokenReadOnly": self.user_token_read_only,
            "groupPolicy": self.group_policy,
            "groupAllowFrom": self.group_allow_from,
            "dm": self.dm.to_nanobot_config(),
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "SlackConfig":
        dm_data = data.get("dm", {})
        return cls(
            enabled=data.get("enabled", False),
            mode=data.get("mode", "socket"),
            webhook_path=data.get("webhookPath", "/slack/events"),
            bot_token=data.get("botToken", ""),
            app_token=data.get("appToken", ""),
            user_token_read_only=data.get("userTokenReadOnly", True),
            group_policy=data.get("groupPolicy", "mention"),
            group_allow_from=data.get("groupAllowFrom", []),
            dm=SlackDMConfig.from_nanobot_config(dm_data) if dm_data else SlackDMConfig(),
        )


@dataclass
class EmailConfig:
    enabled: bool = False
    consent_granted: bool = False
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    from_address: str = ""
    auto_reply_enabled: bool = True
    poll_interval_seconds: int = 30
    mark_seen: bool = True
    max_body_chars: int = 12000
    subject_prefix: str = "Re: "
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "consent_granted": self.consent_granted,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "imap_username": self.imap_username,
            "imap_password": self.imap_password,
            "imap_mailbox": self.imap_mailbox,
            "imap_use_ssl": self.imap_use_ssl,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_password": self.smtp_password,
            "smtp_use_tls": self.smtp_use_tls,
            "smtp_use_ssl": self.smtp_use_ssl,
            "from_address": self.from_address,
            "auto_reply_enabled": self.auto_reply_enabled,
            "poll_interval_seconds": self.poll_interval_seconds,
            "mark_seen": self.mark_seen,
            "max_body_chars": self.max_body_chars,
            "subject_prefix": self.subject_prefix,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmailConfig":
        return cls(
            enabled=data.get("enabled", False),
            consent_granted=data.get("consent_granted", False),
            imap_host=data.get("imap_host", ""),
            imap_port=data.get("imap_port", 993),
            imap_username=data.get("imap_username", ""),
            imap_password=data.get("imap_password", ""),
            imap_mailbox=data.get("imap_mailbox", "INBOX"),
            imap_use_ssl=data.get("imap_use_ssl", True),
            smtp_host=data.get("smtp_host", ""),
            smtp_port=data.get("smtp_port", 587),
            smtp_username=data.get("smtp_username", ""),
            smtp_password=data.get("smtp_password", ""),
            smtp_use_tls=data.get("smtp_use_tls", True),
            smtp_use_ssl=data.get("smtp_use_ssl", False),
            from_address=data.get("from_address", ""),
            auto_reply_enabled=data.get("auto_reply_enabled", True),
            poll_interval_seconds=data.get("poll_interval_seconds", 30),
            mark_seen=data.get("mark_seen", True),
            max_body_chars=data.get("max_body_chars", 12000),
            subject_prefix=data.get("subject_prefix", "Re: "),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "consentGranted": self.consent_granted,
            "imapHost": self.imap_host,
            "imapPort": self.imap_port,
            "imapUsername": self.imap_username,
            "imapPassword": self.imap_password,
            "imapMailbox": self.imap_mailbox,
            "imapUseSsl": self.imap_use_ssl,
            "smtpHost": self.smtp_host,
            "smtpPort": self.smtp_port,
            "smtpUsername": self.smtp_username,
            "smtpPassword": self.smtp_password,
            "smtpUseTls": self.smtp_use_tls,
            "smtpUseSsl": self.smtp_use_ssl,
            "fromAddress": self.from_address,
            "autoReplyEnabled": self.auto_reply_enabled,
            "pollIntervalSeconds": self.poll_interval_seconds,
            "markSeen": self.mark_seen,
            "maxBodyChars": self.max_body_chars,
            "subjectPrefix": self.subject_prefix,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "EmailConfig":
        return cls(
            enabled=data.get("enabled", False),
            consent_granted=data.get("consentGranted", False),
            imap_host=data.get("imapHost", ""),
            imap_port=data.get("imapPort", 993),
            imap_username=data.get("imapUsername", ""),
            imap_password=data.get("imapPassword", ""),
            imap_mailbox=data.get("imapMailbox", "INBOX"),
            imap_use_ssl=data.get("imapUseSsl", True),
            smtp_host=data.get("smtpHost", ""),
            smtp_port=data.get("smtpPort", 587),
            smtp_username=data.get("smtpUsername", ""),
            smtp_password=data.get("smtpPassword", ""),
            smtp_use_tls=data.get("smtpUseTls", True),
            smtp_use_ssl=data.get("smtpUseSsl", False),
            from_address=data.get("fromAddress", ""),
            auto_reply_enabled=data.get("autoReplyEnabled", True),
            poll_interval_seconds=data.get("pollIntervalSeconds", 30),
            mark_seen=data.get("markSeen", True),
            max_body_chars=data.get("maxBodyChars", 12000),
            subject_prefix=data.get("subjectPrefix", "Re: "),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class QQConfig:
    enabled: bool = False
    app_id: str = ""
    secret: str = ""
    allow_from: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "app_id": self.app_id,
            "secret": self.secret,
            "allow_from": self.allow_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QQConfig":
        return cls(
            enabled=data.get("enabled", False),
            app_id=data.get("app_id", ""),
            secret=data.get("secret", ""),
            allow_from=data.get("allow_from", []),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "appId": self.app_id,
            "secret": self.secret,
            "allowFrom": self.allow_from,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "QQConfig":
        return cls(
            enabled=data.get("enabled", False),
            app_id=data.get("appId", ""),
            secret=data.get("secret", ""),
            allow_from=data.get("allowFrom", []),
        )


@dataclass
class MochatMentionConfig:
    require_in_groups: bool = False

    def to_dict(self) -> dict:
        return {"require_in_groups": self.require_in_groups}

    @classmethod
    def from_dict(cls, data: dict) -> "MochatMentionConfig":
        return cls(require_in_groups=data.get("require_in_groups", False))

    def to_nanobot_config(self) -> dict:
        return {"requireInGroups": self.require_in_groups}

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "MochatMentionConfig":
        return cls(require_in_groups=data.get("requireInGroups", False))


@dataclass
class MochatGroupRule:
    require_mention: bool = False

    def to_dict(self) -> dict:
        return {"require_mention": self.require_mention}

    @classmethod
    def from_dict(cls, data: dict) -> "MochatGroupRule":
        return cls(require_mention=data.get("require_mention", False))

    def to_nanobot_config(self) -> dict:
        return {"requireMention": self.require_mention}

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "MochatGroupRule":
        return cls(require_mention=data.get("requireMention", False))


@dataclass
class MochatConfig:
    enabled: bool = False
    base_url: str = "https://mochat.io"
    socket_url: str = ""
    socket_path: str = "/socket.io"
    socket_disable_msgpack: bool = False
    socket_reconnect_delay_ms: int = 1000
    socket_max_reconnect_delay_ms: int = 10000
    socket_connect_timeout_ms: int = 10000
    refresh_interval_ms: int = 30000
    watch_timeout_ms: int = 25000
    watch_limit: int = 100
    retry_delay_ms: int = 500
    max_retry_attempts: int = 0
    claw_token: str = ""
    agent_user_id: str = ""
    sessions: List[str] = field(default_factory=list)
    panels: List[str] = field(default_factory=list)
    allow_from: List[str] = field(default_factory=list)
    mention: MochatMentionConfig = field(default_factory=MochatMentionConfig)
    groups: Dict[str, MochatGroupRule] = field(default_factory=dict)
    reply_delay_mode: str = "non-mention"
    reply_delay_ms: int = 120000

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "socket_url": self.socket_url,
            "socket_path": self.socket_path,
            "socket_disable_msgpack": self.socket_disable_msgpack,
            "socket_reconnect_delay_ms": self.socket_reconnect_delay_ms,
            "socket_max_reconnect_delay_ms": self.socket_max_reconnect_delay_ms,
            "socket_connect_timeout_ms": self.socket_connect_timeout_ms,
            "refresh_interval_ms": self.refresh_interval_ms,
            "watch_timeout_ms": self.watch_timeout_ms,
            "watch_limit": self.watch_limit,
            "retry_delay_ms": self.retry_delay_ms,
            "max_retry_attempts": self.max_retry_attempts,
            "claw_token": self.claw_token,
            "agent_user_id": self.agent_user_id,
            "sessions": self.sessions,
            "panels": self.panels,
            "allow_from": self.allow_from,
            "mention": self.mention.to_dict(),
            "groups": {k: v.to_dict() for k, v in self.groups.items()},
            "reply_delay_mode": self.reply_delay_mode,
            "reply_delay_ms": self.reply_delay_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MochatConfig":
        mention_data = data.get("mention", {})
        groups_data = data.get("groups", {})
        return cls(
            enabled=data.get("enabled", False),
            base_url=data.get("base_url", "https://mochat.io"),
            socket_url=data.get("socket_url", ""),
            socket_path=data.get("socket_path", "/socket.io"),
            socket_disable_msgpack=data.get("socket_disable_msgpack", False),
            socket_reconnect_delay_ms=data.get("socket_reconnect_delay_ms", 1000),
            socket_max_reconnect_delay_ms=data.get("socket_max_reconnect_delay_ms", 10000),
            socket_connect_timeout_ms=data.get("socket_connect_timeout_ms", 10000),
            refresh_interval_ms=data.get("refresh_interval_ms", 30000),
            watch_timeout_ms=data.get("watch_timeout_ms", 25000),
            watch_limit=data.get("watch_limit", 100),
            retry_delay_ms=data.get("retry_delay_ms", 500),
            max_retry_attempts=data.get("max_retry_attempts", 0),
            claw_token=data.get("claw_token", ""),
            agent_user_id=data.get("agent_user_id", ""),
            sessions=data.get("sessions", []),
            panels=data.get("panels", []),
            allow_from=data.get("allow_from", []),
            mention=MochatMentionConfig.from_dict(mention_data) if mention_data else MochatMentionConfig(),
            groups={k: MochatGroupRule.from_dict(v) for k, v in groups_data.items()},
            reply_delay_mode=data.get("reply_delay_mode", "non-mention"),
            reply_delay_ms=data.get("reply_delay_ms", 120000),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "baseUrl": self.base_url,
            "socketUrl": self.socket_url,
            "socketPath": self.socket_path,
            "socketDisableMsgpack": self.socket_disable_msgpack,
            "socketReconnectDelayMs": self.socket_reconnect_delay_ms,
            "socketMaxReconnectDelayMs": self.socket_max_reconnect_delay_ms,
            "socketConnectTimeoutMs": self.socket_connect_timeout_ms,
            "refreshIntervalMs": self.refresh_interval_ms,
            "watchTimeoutMs": self.watch_timeout_ms,
            "watchLimit": self.watch_limit,
            "retryDelayMs": self.retry_delay_ms,
            "maxRetryAttempts": self.max_retry_attempts,
            "clawToken": self.claw_token,
            "agentUserId": self.agent_user_id,
            "sessions": self.sessions,
            "panels": self.panels,
            "allowFrom": self.allow_from,
            "mention": self.mention.to_nanobot_config(),
            "groups": {k: v.to_nanobot_config() for k, v in self.groups.items()},
            "replyDelayMode": self.reply_delay_mode,
            "replyDelayMs": self.reply_delay_ms,
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "MochatConfig":
        mention_data = data.get("mention", {})
        groups_data = data.get("groups", {})
        return cls(
            enabled=data.get("enabled", False),
            base_url=data.get("baseUrl", "https://mochat.io"),
            socket_url=data.get("socketUrl", ""),
            socket_path=data.get("socketPath", "/socket.io"),
            socket_disable_msgpack=data.get("socketDisableMsgpack", False),
            socket_reconnect_delay_ms=data.get("socketReconnectDelayMs", 1000),
            socket_max_reconnect_delay_ms=data.get("socketMaxReconnectDelayMs", 10000),
            socket_connect_timeout_ms=data.get("socketConnectTimeoutMs", 10000),
            refresh_interval_ms=data.get("refreshIntervalMs", 30000),
            watch_timeout_ms=data.get("watchTimeoutMs", 25000),
            watch_limit=data.get("watchLimit", 100),
            retry_delay_ms=data.get("retryDelayMs", 500),
            max_retry_attempts=data.get("maxRetryAttempts", 0),
            claw_token=data.get("clawToken", ""),
            agent_user_id=data.get("agentUserId", ""),
            sessions=data.get("sessions", []),
            panels=data.get("panels", []),
            allow_from=data.get("allowFrom", []),
            mention=MochatMentionConfig.from_nanobot_config(mention_data) if mention_data else MochatMentionConfig(),
            groups={k: MochatGroupRule.from_nanobot_config(v) for k, v in groups_data.items()},
            reply_delay_mode=data.get("replyDelayMode", "non-mention"),
            reply_delay_ms=data.get("replyDelayMs", 120000),
        )


@dataclass
class ChannelsConfig:
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    dingtalk: DingTalkConfig = field(default_factory=DingTalkConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    qq: QQConfig = field(default_factory=QQConfig)
    mochat: MochatConfig = field(default_factory=MochatConfig)

    def to_dict(self) -> dict:
        return {
            "whatsapp": self.whatsapp.to_dict(),
            "telegram": self.telegram.to_dict(),
            "discord": self.discord.to_dict(),
            "feishu": self.feishu.to_dict(),
            "dingtalk": self.dingtalk.to_dict(),
            "slack": self.slack.to_dict(),
            "email": self.email.to_dict(),
            "qq": self.qq.to_dict(),
            "mochat": self.mochat.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelsConfig":
        return cls(
            whatsapp=WhatsAppConfig.from_dict(data.get("whatsapp", {})),
            telegram=TelegramConfig.from_dict(data.get("telegram", {})),
            discord=DiscordConfig.from_dict(data.get("discord", {})),
            feishu=FeishuConfig.from_dict(data.get("feishu", {})),
            dingtalk=DingTalkConfig.from_dict(data.get("dingtalk", {})),
            slack=SlackConfig.from_dict(data.get("slack", {})),
            email=EmailConfig.from_dict(data.get("email", {})),
            qq=QQConfig.from_dict(data.get("qq", {})),
            mochat=MochatConfig.from_dict(data.get("mochat", {})),
        )

    def to_nanobot_config(self) -> dict:
        return {
            "whatsapp": self.whatsapp.to_nanobot_config(),
            "telegram": self.telegram.to_nanobot_config(),
            "discord": self.discord.to_nanobot_config(),
            "feishu": self.feishu.to_nanobot_config(),
            "dingtalk": self.dingtalk.to_nanobot_config(),
            "slack": self.slack.to_nanobot_config(),
            "email": self.email.to_nanobot_config(),
            "qq": self.qq.to_nanobot_config(),
            "mochat": self.mochat.to_nanobot_config(),
        }

    @classmethod
    def from_nanobot_config(cls, data: dict) -> "ChannelsConfig":
        return cls(
            whatsapp=WhatsAppConfig.from_nanobot_config(data.get("whatsapp", {})),
            telegram=TelegramConfig.from_nanobot_config(data.get("telegram", {})),
            discord=DiscordConfig.from_nanobot_config(data.get("discord", {})),
            feishu=FeishuConfig.from_nanobot_config(data.get("feishu", {})),
            dingtalk=DingTalkConfig.from_nanobot_config(data.get("dingtalk", {})),
            slack=SlackConfig.from_nanobot_config(data.get("slack", {})),
            email=EmailConfig.from_nanobot_config(data.get("email", {})),
            qq=QQConfig.from_nanobot_config(data.get("qq", {})),
            mochat=MochatConfig.from_nanobot_config(data.get("mochat", {})),
        )

    def get_enabled_channels(self) -> List[str]:
        enabled = []
        if self.whatsapp.enabled:
            enabled.append("whatsapp")
        if self.telegram.enabled:
            enabled.append("telegram")
        if self.discord.enabled:
            enabled.append("discord")
        if self.feishu.enabled:
            enabled.append("feishu")
        if self.dingtalk.enabled:
            enabled.append("dingtalk")
        if self.slack.enabled:
            enabled.append("slack")
        if self.email.enabled:
            enabled.append("email")
        if self.qq.enabled:
            enabled.append("qq")
        if self.mochat.enabled:
            enabled.append("mochat")
        return enabled


CHANNEL_INFO = {
    "whatsapp": {
        "name": "WhatsApp",
        "description": "消息平台桥接，需要运行 bridge 服务",
        "icon": "💬",
    },
    "telegram": {
        "name": "Telegram",
        "description": "Telegram Bot API 集成",
        "icon": "✈️",
    },
    "discord": {
        "name": "Discord",
        "description": "Discord Bot 集成",
        "icon": "🎮",
    },
    "feishu": {
        "name": "飞书 (Feishu)",
        "description": "飞书开放平台应用集成",
        "icon": "🐦",
    },
    "dingtalk": {
        "name": "钉钉 (DingTalk)",
        "description": "钉钉 Stream 模式集成",
        "icon": "📌",
    },
    "slack": {
        "name": "Slack",
        "description": "Slack Socket Mode 集成",
        "icon": "💼",
    },
    "email": {
        "name": "Email",
        "description": "IMAP/SMTP 邮件收发",
        "icon": "📧",
    },
    "qq": {
        "name": "QQ",
        "description": "QQ 频道机器人",
        "icon": "🐧",
    },
    "mochat": {
        "name": "Mochat",
        "description": "Mochat 多平台消息集成",
        "icon": "📱",
    },
}
