hl.layer_rule({
    match = {namespace = "^quickshell:confirm-close$"},
    blur = true,
    ignore_alpha = 0.5,
    no_anim = true,
})

-- Internet Swap window (managed integration)
hl.window_rule({
    match = {class = "^internet-swap$"},
    float = true,
    center = true,
    size = {"480", "720"},
})
