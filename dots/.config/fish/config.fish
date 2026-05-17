set -g fish_greeting ""

set -gx EDITOR nvim
set -gx TERMINAL kitty

function fish_greeting
    echo ""

    set_color cyan
    echo "If the code doesnt run blame the ACL"

    echo ""

    set_color FF6B6B
    echo "Welcome to b(ash)"

    echo ""
end

function fish_prompt
    set_color green
    echo -n $USER
    set_color magenta
    echo -n "@"
    set_color blue
    echo -n $hostname
    set_color white
    echo -n " > "
    set_color cyan
    echo -n (basename (pwd))
    set_color magenta
    echo -n " ❯"
    set_color normal
    echo -n " "
end