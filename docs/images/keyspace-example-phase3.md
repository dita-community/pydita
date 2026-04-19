# Key Space Construction Example — Phase 3: Push Down

`PushDownVisitor` walks pre-order (root first). Each scope prepends all of its own key definitions into each direct child. Because prepending gives the incoming definitions higher priority, ancestor definitions **win** over same-name descendant definitions.

```mermaid
flowchart LR
    subgraph KS["Key Spaces (after Phase 3 — final state)"]
        direction TB
        subgraph ROOT["Root Scope (anonymous) — unchanged"]
            R_logo["logo: corp-logo.png"]
            R_PL["product.logo: prod-logo.png"]
            R_PT["product.title: prod-title.dita"]
            R_PWI["product.widget.icon: widget-icon.png"]
        end
        subgraph PROD["Scope: product"]
            P_logo_win["logo: corp-logo.png  — inherited, WINS"]
            P_logo_lose["logo: prod-logo.png  — local, overridden"]
            P_title["title: prod-title.dita"]
            P_WI["widget.icon: widget-icon.png"]
            P_PL["product.logo: prod-logo.png"]
            P_PT["product.title: prod-title.dita"]
            P_PWI["product.widget.icon: widget-icon.png"]
        end
        subgraph WIDG["Scope: widget"]
            W_icon["icon: widget-icon.png"]
            W_logo["logo: corp-logo.png  — inherited through product"]
            W_title["title: prod-title.dita  — inherited from product"]
        end
    end

    subgraph MAP["DITA Map Tree"]
        direction TB
        Mroot(["Root Map"])
        Mrootkey["keydef\nkeys=logo\nhref=corp-logo.png"]
        Mprod["topicref\nkeyscope=product"]
        MPK1["keydef\nkeys=logo\nhref=prod-logo.png"]
        MPK2["keydef\nkeys=title\nhref=prod-title.dita"]
        Mwidg["topicref\nkeyscope=widget"]
        MWK["keydef\nkeys=icon\nhref=widget-icon.png"]

        Mroot --> Mrootkey
        Mroot --> Mprod
        Mprod --> MPK1
        Mprod --> MPK2
        Mprod --> Mwidg
        Mwidg --> MWK
    end

    ROOT -->|"1. root prepends its keys into product.\nlogo collision: root wins."| PROD
    PROD -->|"2. product (now including root keys)\nprepends its keys into widget."| WIDG

    classDef local fill:#d4edda,stroke:#28a745,color:#155724
    classDef pullup fill:#cce5ff,stroke:#004085,color:#004085
    classDef pushdown fill:#fff3cd,stroke:#856404,color:#533f03
    classDef overridden fill:#f8d7da,stroke:#721c24,color:#721c24,stroke-dasharray: 5 3
    classDef scoperef fill:#e2e3e5,stroke:#6c757d,color:#383d41
    classDef keydef fill:#e2e3e5,stroke:#6c757d,color:#383d41
    classDef maproot fill:#dee2e6,stroke:#495057,color:#212529

    class R_logo,P_title,W_icon local
    class R_PL,R_PT,R_PWI,P_WI pullup
    class P_logo_win,P_PL,P_PT,P_PWI,W_logo,W_title pushdown
    class P_logo_lose overridden
    class Mprod,Mwidg scoperef
    class Mrootkey,MPK1,MPK2,MWK keydef
    class Mroot maproot
```

**What changed from Phase 2**

| Scope | Effect |
|-------|--------|
| Root | Unchanged |
| `product` | Received root's keys prepended. `logo` now resolves to `corp-logo.png` (root wins). Also gained `product.logo`, `product.title`, `product.widget.icon`. |
| `widget` | Received product's full key set (which already includes root's keys). `logo` and `title` are now visible unqualified. |

**Legend**

| Color | Meaning |
|-------|---------|
| Green | Locally defined (Phase 1) |
| Blue | Qualified alias from pull-up (Phase 2) |
| Yellow | Inherited via push-down (this phase) |
| Red dashed | Local definition that was overridden — still in the list at lower priority, but never returned by `resolveKey()` |

**The override in detail**

Before push-down, `product`'s `logo` list was: `[prod-logo.png]`.

After root prepends its definitions, the list becomes: `[corp-logo.png, prod-logo.png]`.

`resolveKey("logo")` returns index 0 — `corp-logo.png` — regardless of where in the `product` scope the reference appears.
