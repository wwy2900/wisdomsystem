from __future__ import annotations

from langchain_core.tools import tool

from agent.tools.runtime import SourceReference, add_source_reference, get_request_user_id, run_audited_tool
from services.customer_support_service import CustomerSupportService


customer_support_service = CustomerSupportService()


def _require_user_id() -> str:
    user_id = get_request_user_id()
    if not user_id:
        raise RuntimeError("Authenticated user context is required for customer support tools.")
    return user_id


def _add_business_source(
    tool_name: str,
    title: str,
    snippet: str,
    record_id: str,
    metadata: dict[str, object] | None = None,
):
    add_source_reference(
        SourceReference(
            source_type="business_tool",
            title=title,
            snippet=snippet,
            tool_name=tool_name,
            record_id=record_id,
            metadata=metadata or {},
        )
    )


def _format_device_summary(device: dict[str, object]) -> str:
    status = device.get("status") or "unknown"
    purchase_date = device.get("purchase_date") or "unknown"
    warranty = device.get("warranty_expires_at") or "unknown"
    serial_number = device.get("serial_number") or "N/A"
    return (
        f"{device.get('product_name')} ({device.get('model')})\n"
        f"Device ID: {device.get('device_id')}\n"
        f"Status: {status}\n"
        f"Serial Number: {serial_number}\n"
        f"Purchase Date: {purchase_date}\n"
        f"Warranty Expires: {warranty}"
    )


@tool
def lookup_user_devices() -> str:
    """Look up the current user's bound robot devices, models, status, purchase time, and warranty time."""

    def _callback():
        user_id = _require_user_id()
        devices = customer_support_service.list_user_devices(user_id)
        if not devices:
            return "No bound device record was found for the current account."

        for device in devices:
            _add_business_source(
                tool_name="lookup_user_devices",
                title=f"{device['product_name']} ({device['model']})",
                snippet=_format_device_summary(device),
                record_id=str(device["device_id"]),
                metadata={
                    "device_id": device["device_id"],
                    "status": device.get("status"),
                    "warranty_expires_at": device.get("warranty_expires_at"),
                },
            )

        sections = [_format_device_summary(device) for device in devices]
        return "\n\n".join(sections)

    return run_audited_tool("lookup_user_devices", args={}, callback=_callback)


@tool
def lookup_device_consumables(device_id: str = "") -> str:
    """Look up the remaining life and maintenance reminders for the current user's device consumables."""

    def _callback():
        user_id = _require_user_id()
        resolved_device_id = device_id.strip() or None
        device, consumables = customer_support_service.list_device_consumables(user_id, device_id=resolved_device_id)
        if not device:
            return "No bound device was found for the current account, so consumable status is unavailable."
        if not consumables:
            return f"No consumable maintenance record was found for device {device['device_id']}."

        lines = [f"{device['product_name']} ({device['model']}) consumables:"]
        for record in consumables:
            line = (
                f"- {record['consumable_type']}: status={record['status']}, "
                f"remaining_percent={record.get('remaining_percent')}, "
                f"remaining_days={record.get('remaining_days')}, "
                f"tip={record.get('maintenance_tip') or 'N/A'}"
            )
            lines.append(line)
            _add_business_source(
                tool_name="lookup_device_consumables",
                title=f"{device['product_name']} - {record['consumable_type']}",
                snippet=line,
                record_id=str(record["id"]),
                metadata={
                    "device_id": device["device_id"],
                    "consumable_type": record.get("consumable_type"),
                    "status": record.get("status"),
                },
            )
        return "\n".join(lines)

    return run_audited_tool(
        "lookup_device_consumables",
        args={"device_id": device_id},
        callback=_callback,
    )


@tool
def lookup_service_policy(query: str) -> str:
    """Look up after-sales, warranty, return, repair, and accessory purchase policies."""

    def _callback():
        records = customer_support_service.search_service_policies(query)
        if not records:
            return f"No matching service policy was found for query: {query}"

        lines = []
        for record in records:
            snippet = str(record.get("content", ""))
            lines.append(f"{record.get('title')}: {snippet}")
            _add_business_source(
                tool_name="lookup_service_policy",
                title=str(record.get("title", "Service policy")),
                snippet=snippet,
                record_id=str(record.get("record_id", record.get("title", "policy"))),
                metadata={"category": record.get("category"), "keywords": record.get("keywords", [])},
            )
        return "\n\n".join(lines)

    return run_audited_tool(
        "lookup_service_policy",
        args={"query": query},
        callback=_callback,
    )


@tool
def lookup_service_channels(query: str = "") -> str:
    """Look up customer support contact channels, service outlets, delivery addresses, and service hours."""

    def _callback():
        records = customer_support_service.search_service_channels(query)
        if not records:
            return "No matching service channel was found."

        lines = []
        for record in records:
            snippet = (
                f"Contact: {record.get('contact')} | Hours: {record.get('service_hours')} | "
                f"Address: {record.get('address', 'N/A')}"
            )
            lines.append(f"{record.get('title')}: {snippet}")
            _add_business_source(
                tool_name="lookup_service_channels",
                title=str(record.get("title", "Service channel")),
                snippet=snippet,
                record_id=str(record.get("record_id", record.get("title", "channel"))),
                metadata={
                    "channel_type": record.get("channel_type"),
                    "service_hours": record.get("service_hours"),
                },
            )
        return "\n\n".join(lines)

    return run_audited_tool(
        "lookup_service_channels",
        args={"query": query},
        callback=_callback,
    )
