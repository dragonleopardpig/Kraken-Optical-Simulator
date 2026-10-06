"""Which interface KrakenOS opens in, as a form both interfaces show (bugs/0971).

The user asked for both the Tk and the Qt interface to stay available, "let user to choose his
usage preference". The choice is a saved per-user preference (`user_preferences`, read by
`launcher.py`); this form is how it is seen and changed from inside either interface. It takes
effect at the next start -- the running interface is not swapped under the user.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Interface Preference"
ASK = "Ask me at every start"


def running_shell(owner) -> str:
    """"qt" or "tk" -- the interface ``owner`` is being shown in; "" under a scripted host."""
    from KrakenOS.UI.uihost import host_of

    name = type(host_of(owner)).__name__
    return {"QtUiHost": "qt", "TkUiHost": "tk"}.get(name, "")


def build_interface_preference_form(owner) -> RowForm:
    """``owner`` is the editor. One choice: an interface that can run here, or to be asked."""
    from KrakenOS.UI import launcher, user_preferences

    available = launcher.available_shells()
    names = {shell: launcher.SHELLS[shell][0] for shell in launcher.SHELLS}
    offered = [shell for shell in launcher.ASK_ORDER if not available.get(shell, "x")]
    choices = tuple(names[shell] for shell in offered) + (ASK,)
    saved = str(user_preferences.get(launcher.PREFERENCE_KEY, "") or "").strip().lower()
    running = running_shell(owner)

    def shell_of(text: str) -> "str | None":
        return next((shell for shell in offered if names[shell] == text), None)

    def validate(values: dict) -> list:
        return [] if values.get("shell") in choices else [f"Choose one of: {', '.join(choices)}."]

    def describe(values: dict) -> str:
        shell = shell_of(values.get("shell", ""))
        if shell is None:
            return "KrakenOS will ask which interface to open, each time it starts."
        return f"KrakenOS will open in the {names[shell]} the next time it starts."

    def apply(values: dict) -> str:
        problems = validate(values)
        if problems:
            raise FormRefused(problems[0])
        problem = user_preferences.set_value(launcher.PREFERENCE_KEY, shell_of(values["shell"]))
        if problem:
            raise FormRefused(problem)
        now = f" This window stays the {names[running]}." if running in names else ""
        return describe(values) + now

    about = "\n".join(f"{names[shell]}: {launcher.SHELLS[shell][1]}" for shell in offered)
    missing = "\n".join(f"The {names[shell]} cannot run here: {reason}." for shell, reason in available.items() if reason)
    return RowForm(
        title=TITLE,
        row_index=-1,
        fields=(FormField("shell", "Open KrakenOS in", kind="choice", choices=choices, width=24),
                FormField("about", "", kind="static")),
        values={"shell": names[saved] if saved in offered else ASK,
                "about": about + ("\n" + missing if missing else "")},
        summary=("KrakenOS has two interfaces over the same program. Choose the one it opens in when started with "
                 "`python -m KrakenOS.UI`; `--shell tk` or `--shell qt` on the command line overrides it for one run."
                 + (f" Running now: the {names[running]}." if running in names else "")),
        validate=validate,
        apply=apply,
        describe=describe,
    )


build_interface_preference_form.TITLE = TITLE
