from __future__ import annotations

from datetime import datetime, timedelta, timezone

CUSTOMER_ID = "mock-customer"

LIBRARIES = [
    {"id": "ACTIVE_US", "alias": "ACTIVE_US", "name": "Active Matters (US)", "description": "Primary US production library"},
    {"id": "ARCHIVE_US", "alias": "ARCHIVE_US", "name": "Archived Matters (US)", "description": "Closed US matters"},
    {"id": "EU_WORK", "alias": "EU_WORK", "name": "EU Work", "description": "European matters and regulatory files"},
]

USERS = [
    {"id": "jchen", "name": "Jordan Chen", "email": "jordan.chen@example.test", "full_name": "Jordan Chen"},
    {"id": "apatel", "name": "Avery Patel", "email": "avery.patel@example.test", "full_name": "Avery Patel"},
    {"id": "mrivera", "name": "Morgan Rivera", "email": "morgan.rivera@example.test", "full_name": "Morgan Rivera"},
    {"id": "sklein", "name": "Sam Klein", "email": "sam.klein@example.test", "full_name": "Sam Klein"},
    {"id": "lwoods", "name": "Lee Woods", "email": "lee.woods@example.test", "full_name": "Lee Woods"},
    {"id": "tnguyen", "name": "Taylor Nguyen", "email": "taylor.nguyen@example.test", "full_name": "Taylor Nguyen"},
]

ME = {"id": "jchen", "name": "Jordan Chen", "email": "jordan.chen@example.test", "full_name": "Jordan Chen"}

CLIENTS = [
    {"id": "412117", "name": "Acme Corporation"},
    {"id": "500220", "name": "Northwind Traders"},
    {"id": "778801", "name": "Contoso Health"},
    {"id": "990010", "name": "Fabrikam Energy"},
    {"id": "314159", "name": "Litware Labs"},
]

MATTERS = {
    "412117-0001": {"client_id": "412117", "client_name": "Acme Corporation", "matter_id": "0001", "matter_name": "Project Falcon Acquisition"},
    "412117-0002": {"client_id": "412117", "client_name": "Acme Corporation", "matter_id": "0002", "matter_name": "Employment Policy Refresh"},
    "500220-0007": {"client_id": "500220", "client_name": "Northwind Traders", "matter_id": "0007", "matter_name": "Supply Agreement Renewal"},
    "778801-0012": {"client_id": "778801", "client_name": "Contoso Health", "matter_id": "0012", "matter_name": "HIPAA Incident Response"},
    "778801-0015": {"client_id": "778801", "client_name": "Contoso Health", "matter_id": "0015", "matter_name": "Provider Network Dispute"},
    "990010-0003": {"client_id": "990010", "client_name": "Fabrikam Energy", "matter_id": "0003", "matter_name": "Wind Farm Financing"},
    "990010-0004": {"client_id": "990010", "client_name": "Fabrikam Energy", "matter_id": "0004", "matter_name": "Regulatory Compliance Review"},
    "314159-0009": {"client_id": "314159", "client_name": "Litware Labs", "matter_id": "0009", "matter_name": "Patent Portfolio Strategy"},
}

CLASS_DESCRIPTIONS = {
    "DOC": "Document",
    "EMAIL": "Email",
    "PLEADING": "Pleading",
    "CONTRACT": "Contract",
    "MEMO": "Memorandum",
    "PRES": "Presentation",
}

PRACTICES = {
    "CORP": "Corporate",
    "EMPL": "Employment",
    "COMM": "Commercial",
    "HLTH": "Healthcare",
    "LIT": "Litigation",
    "FIN": "Finance",
    "REG": "Regulatory",
    "IP": "Intellectual Property",
}

JURISDICTIONS = {"US-DE": "Delaware", "US-NY": "New York", "US-CA": "California", "EU-DE": "Germany", "EU-IE": "Ireland"}

WORKSPACES = [
    {"id": "ACTIVE_US!9001", "library": "ACTIVE_US", "name": "Acme Corporation - Project Falcon Acquisition", "custom1": "412117", "custom1_description": "Acme Corporation", "custom2": "0001", "custom2_description": "Project Falcon Acquisition"},
    {"id": "ACTIVE_US!9002", "library": "ACTIVE_US", "name": "Northwind Traders - Supply Agreement Renewal", "custom1": "500220", "custom1_description": "Northwind Traders", "custom2": "0007", "custom2_description": "Supply Agreement Renewal"},
    {"id": "EU_WORK!9101", "library": "EU_WORK", "name": "Fabrikam Energy - Regulatory Compliance Review", "custom1": "990010", "custom1_description": "Fabrikam Energy", "custom2": "0004", "custom2_description": "Regulatory Compliance Review"},
    {"id": "ACTIVE_US!9003", "library": "ACTIVE_US", "name": "Contoso Health - HIPAA Incident Response", "custom1": "778801", "custom1_description": "Contoso Health", "custom2": "0012", "custom2_description": "HIPAA Incident Response"},
]

FOLDERS = [
    {"id": "ACTIVE_US!91001", "workspace_id": "ACTIVE_US!9001", "parent_id": "ACTIVE_US!9001", "name": "Agreements", "type": "regular"},
    {"id": "ACTIVE_US!91002", "workspace_id": "ACTIVE_US!9001", "parent_id": "ACTIVE_US!9001", "name": "Due Diligence", "type": "regular"},
    {"id": "ACTIVE_US!92001", "workspace_id": "ACTIVE_US!9002", "parent_id": "ACTIVE_US!9002", "name": "Contracts", "type": "regular"},
    {"id": "EU_WORK!93001", "workspace_id": "EU_WORK!9101", "parent_id": "EU_WORK!9101", "name": "Regulatory", "type": "regular"},
    {"id": "ACTIVE_US!94001", "workspace_id": "ACTIVE_US!9003", "parent_id": "ACTIVE_US!9003", "name": "Incident Response", "type": "regular"},
]

now = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
DOCUMENTS: list[dict] = []
TEXTS: dict[str, str] = {}
VERSIONS: dict[str, list[dict]] = {}

def _add(num: int, lib: str, title: str, matter_key: str, author: str, klass: str, practice: str, jurisdiction: str, ext: str = "docx", is_email: bool = False, folder_id: str | None = None, workspace_id: str | None = None, days: int = 0, text: str | None = None) -> None:
    matter = MATTERS[matter_key]
    author_row = next(u for u in USERS if u["id"] == author)
    version = 1 + (num % 3)
    doc_id = f"{lib}!{num}.{version}"
    modified = now - timedelta(days=days, hours=num % 7)
    document = {
        "id": doc_id,
        "library": lib,
        "database": lib,
        "document_number": str(num),
        "version": version,
        "name": title,
        "title": title,
        "extension": "eml" if is_email else ext,
        "type": "email" if is_email else "document",
        "is_email": is_email,
        "owner": author,
        "author": author,
        "author_description": author_row["name"],
        "class": "EMAIL" if is_email else klass,
        "class_description": CLASS_DESCRIPTIONS["EMAIL" if is_email else klass],
        "custom1": matter["client_id"],
        "custom1_description": matter["client_name"],
        "custom2": matter["matter_id"],
        "custom2_description": matter["matter_name"],
        "custom3": practice,
        "custom3_description": PRACTICES[practice],
        "custom4": jurisdiction,
        "custom4_description": JURISDICTIONS[jurisdiction],
        "workspace_id": workspace_id,
        "workspace_name": f"{matter['client_name']} - {matter['matter_name']}",
        "folder_id": folder_id,
        "size": 42000 + (num * 17),
        "updated_at": modified.isoformat().replace("+00:00", "Z"),
        "created_at": (modified - timedelta(days=30 + (num % 11))).isoformat().replace("+00:00", "Z"),
    }
    DOCUMENTS.append(document)
    TEXTS[doc_id] = text or f"{title}. Client {matter['client_name']} matter {matter['matter_name']}. This mock extracted text includes key terms for search, diligence, contract review, and grounded agent answers. Document number {num}."
    VERSIONS[doc_id] = [
        {"id": f"{lib}!{num}.{v}", "document_number": str(num), "version": v, "updated_at": (modified - timedelta(days=(version - v) * 4)).isoformat().replace("+00:00", "Z"), "size": 40000 + (num * 13) + v}
        for v in range(1, version + 1)
    ]

_add(1001, "ACTIVE_US", "Project Falcon Merger Agreement", "412117-0001", "jchen", "CONTRACT", "CORP", "US-DE", folder_id="ACTIVE_US!91001", workspace_id="ACTIVE_US!9001", days=1, text="Merger Agreement for Project Falcon. Sections cover purchase price, indemnification caps, survival periods, escrow, closing deliverables, and governing law.")
_add(1002, "ACTIVE_US", "Project Falcon Disclosure Schedules", "412117-0001", "apatel", "DOC", "CORP", "US-DE", folder_id="ACTIVE_US!91002", workspace_id="ACTIVE_US!9001", days=2)
_add(1003, "ACTIVE_US", "Acme Board Approval Minutes", "412117-0001", "mrivera", "DOC", "CORP", "US-DE", folder_id="ACTIVE_US!91002", workspace_id="ACTIVE_US!9001", days=4)
_add(1004, "ACTIVE_US", "Email Re Project Falcon Signing Timeline", "412117-0001", "sklein", "EMAIL", "CORP", "US-DE", is_email=True, folder_id="ACTIVE_US!91001", workspace_id="ACTIVE_US!9001", days=5)
_add(1005, "ACTIVE_US", "Acme Employment Handbook Update", "412117-0002", "tnguyen", "MEMO", "EMPL", "US-CA", days=8)
_add(1006, "ACTIVE_US", "Remote Work Policy Analysis", "412117-0002", "lwoods", "MEMO", "EMPL", "US-CA", days=12)
_add(1007, "ACTIVE_US", "Email Re Handbook Rollout", "412117-0002", "tnguyen", "EMAIL", "EMPL", "US-CA", is_email=True, days=13)
_add(1008, "ACTIVE_US", "Northwind Master Supply Agreement", "500220-0007", "apatel", "CONTRACT", "COMM", "US-NY", folder_id="ACTIVE_US!92001", workspace_id="ACTIVE_US!9002", days=3)
_add(1009, "ACTIVE_US", "Northwind Pricing Addendum", "500220-0007", "jchen", "CONTRACT", "COMM", "US-NY", folder_id="ACTIVE_US!92001", workspace_id="ACTIVE_US!9002", days=9)
_add(1010, "ACTIVE_US", "Email Re Northwind Renewal Negotiation", "500220-0007", "mrivera", "EMAIL", "COMM", "US-NY", is_email=True, folder_id="ACTIVE_US!92001", workspace_id="ACTIVE_US!9002", days=10)
_add(1011, "ACTIVE_US", "Contoso HIPAA Incident Chronology", "778801-0012", "lwoods", "DOC", "HLTH", "US-NY", folder_id="ACTIVE_US!94001", workspace_id="ACTIVE_US!9003", days=6)
_add(1012, "ACTIVE_US", "Contoso Breach Notification Memo", "778801-0012", "sklein", "MEMO", "HLTH", "US-NY", folder_id="ACTIVE_US!94001", workspace_id="ACTIVE_US!9003", days=7)
_add(1013, "ACTIVE_US", "Email Re Contoso Regulator Call", "778801-0012", "lwoods", "EMAIL", "HLTH", "US-NY", is_email=True, folder_id="ACTIVE_US!94001", workspace_id="ACTIVE_US!9003", days=11)
_add(1014, "ACTIVE_US", "Provider Network Complaint", "778801-0015", "mrivera", "PLEADING", "LIT", "US-NY", days=14)
_add(1015, "ACTIVE_US", "Provider Network Settlement Term Sheet", "778801-0015", "apatel", "DOC", "LIT", "US-NY", days=16)
_add(2001, "EU_WORK", "Fabrikam Wind Farm Credit Agreement", "990010-0003", "jchen", "CONTRACT", "FIN", "EU-IE", days=15)
_add(2002, "EU_WORK", "Fabrikam Security Package Summary", "990010-0003", "apatel", "MEMO", "FIN", "EU-IE", days=18)
_add(2003, "EU_WORK", "Fabrikam Environmental Permit Review", "990010-0004", "sklein", "MEMO", "REG", "EU-DE", folder_id="EU_WORK!93001", workspace_id="EU_WORK!9101", days=5)
_add(2004, "EU_WORK", "EU Regulatory Compliance Checklist", "990010-0004", "lwoods", "DOC", "REG", "EU-DE", folder_id="EU_WORK!93001", workspace_id="EU_WORK!9101", days=17)
_add(2005, "EU_WORK", "Email Re German Regulator Questions", "990010-0004", "sklein", "EMAIL", "REG", "EU-DE", is_email=True, folder_id="EU_WORK!93001", workspace_id="EU_WORK!9101", days=20)
_add(2006, "EU_WORK", "Litware Patent Landscape", "314159-0009", "tnguyen", "PRES", "IP", "EU-DE", days=19)
_add(2007, "EU_WORK", "Litware Invention Assignment Review", "314159-0009", "mrivera", "DOC", "IP", "EU-DE", days=21)
_add(3001, "ARCHIVE_US", "Closed Acme Integration Plan", "412117-0001", "jchen", "DOC", "CORP", "US-DE", days=90)
_add(3002, "ARCHIVE_US", "Archived Northwind Negotiation Notes", "500220-0007", "apatel", "MEMO", "COMM", "US-NY", days=120)
_add(3003, "ARCHIVE_US", "Archived Contoso Motion to Dismiss", "778801-0015", "sklein", "PLEADING", "LIT", "US-NY", days=150)

# ---------------------------------------------------------------------------
# Bulk synthetic data — exercises the 500+ default page + "Load more", and gives
# Recent Matters, folders, and clients real volume. Curated 1001–3003 above stay
# intact for named demos (Project Falcon, Northwind, Contoso, Fabrikam, Litware).
# Deterministic (no random) so redeploys produce identical ids.
# ---------------------------------------------------------------------------
_EXTRA_CLIENTS = [
    ("620045", "Globex Manufacturing"),
    ("730112", "Initech Software"),
    ("840233", "Umbrella Logistics"),
    ("915566", "Soylent Foods"),
    ("102938", "Wayne Enterprises"),
    ("564738", "Stark Industries"),
    ("889900", "Wonka Industries"),
    ("276543", "Hooli Platforms"),
    ("334410", "Cyberdyne Robotics"),
]
for _cid, _cname in _EXTRA_CLIENTS:
    CLIENTS.append({"id": _cid, "name": _cname})

_MATTER_NAMES = [
    "Series B Financing", "Trademark Opposition", "Data Processing Addendum",
    "Vendor Master Services", "Shareholder Dispute", "Asset Purchase",
    "Commercial Lease Review", "Export Controls Audit", "Benefits Plan Restatement",
    "Cybersecurity Incident", "Antitrust Clearance", "Joint Venture Formation",
    "Credit Facility Amendment", "Product Recall Response", "Executive Compensation",
]
_FOLDER_NAMES = ["Agreements", "Correspondence", "Diligence", "Pleadings", "Research"]
_TITLE_PREFIXES = ["Draft", "Executed", "Revised", "Final", "Summary of", "Analysis of", "Notes on", "Checklist for", "Memo re", "Report on"]
_TITLE_SUBJECTS = ["Agreement", "Indemnification", "Diligence", "Compliance", "Governance", "Disclosure", "Settlement", "License", "Amendment", "Schedule", "Addendum", "Policy", "Opinion", "Term Sheet"]
_PRACTICE_KEYS = list(PRACTICES.keys())
_CLASS_KEYS = ["CONTRACT", "MEMO", "DOC", "PLEADING", "PRES"]
_JUR_KEYS = list(JURISDICTIONS.keys())
_USER_IDS = [u["id"] for u in USERS]
_LIB_CYCLE = ["ACTIVE_US", "ACTIVE_US", "EU_WORK", "ARCHIVE_US"]

# Build matters + one workspace per matter + a couple of folders per workspace.
_bulk_targets: list[tuple[str, str, str, list[str]]] = []  # (matter_key, library, workspace_id, folder_ids)
_ws_seq = 9500
_folder_seq = 95000
for _ci, _client in enumerate(list(CLIENTS)):
    for _mi in range(4):
        _matter_num = f"{1000 + _ci * 10 + _mi:04d}"
        _key = f"{_client['id']}-{_matter_num}"
        if _key in MATTERS:
            continue
        _mname = _MATTER_NAMES[(_ci * 4 + _mi) % len(_MATTER_NAMES)]
        MATTERS[_key] = {"client_id": _client["id"], "client_name": _client["name"], "matter_id": _matter_num, "matter_name": _mname}
        _lib = _LIB_CYCLE[(_ci + _mi) % len(_LIB_CYCLE)]
        _ws_id = f"{_lib}!{_ws_seq}"
        _ws_seq += 1
        WORKSPACES.append({
            "id": _ws_id, "library": _lib, "name": f"{_client['name']} - {_mname}",
            "custom1": _client["id"], "custom1_description": _client["name"],
            "custom2": _matter_num, "custom2_description": _mname,
        })
        _ws_folders: list[str] = []
        for _fi in range(2):
            _fid = f"{_lib}!{_folder_seq}"
            _folder_seq += 1
            _fname = _FOLDER_NAMES[(_mi + _fi) % len(_FOLDER_NAMES)]
            FOLDERS.append({"id": _fid, "workspace_id": _ws_id, "parent_id": _ws_id, "name": _fname, "type": "regular"})
            _ws_folders.append(_fid)
        _bulk_targets.append((_key, _lib, _ws_id, _ws_folders))

# Generate 600+ documents so an unfiltered Documents search exceeds the 500 default page.
_BULK_START = 5000
_BULK_COUNT = 640
_BULK_EXTS = ["docx", "pdf", "xlsx", "pptx", "docx", "pdf", "txt", "docx"]
for _n in range(_BULK_START, _BULK_START + _BULK_COUNT):
    _key, _lib, _ws_id, _ws_folders = _bulk_targets[_n % len(_bulk_targets)]
    _matter_name = MATTERS[_key]["matter_name"]
    _prefix = _TITLE_PREFIXES[_n % len(_TITLE_PREFIXES)]
    _subject = _TITLE_SUBJECTS[(_n // 2) % len(_TITLE_SUBJECTS)]
    _is_email = (_n % 9 == 0)
    _title = f"{_prefix} {_subject} – {_matter_name} #{_n}"
    _author = _USER_IDS[_n % len(_USER_IDS)]
    _klass = _CLASS_KEYS[_n % len(_CLASS_KEYS)]
    _practice = _PRACTICE_KEYS[_n % len(_PRACTICE_KEYS)]
    _jur = _JUR_KEYS[_n % len(_JUR_KEYS)]
    _folder_id = _ws_folders[_n % len(_ws_folders)]
    _ext = _BULK_EXTS[_n % len(_BULK_EXTS)]
    _add(
        _n, _lib, _title, _key, _author, _klass, _practice, _jur,
        ext=_ext, is_email=_is_email, folder_id=_folder_id, workspace_id=_ws_id, days=(_n % 200),
    )

# Attach direct document children for browse endpoints.
CHILDREN_BY_PARENT: dict[str, list[dict]] = {}
for folder in FOLDERS:
    CHILDREN_BY_PARENT.setdefault(folder["parent_id"], []).append({**folder, "container_type": "folder"})
for doc in DOCUMENTS:
    parent = doc.get("folder_id") or doc.get("workspace_id")
    if parent:
        CHILDREN_BY_PARENT.setdefault(parent, []).append({**doc, "container_type": "document"})
