return {
  {
    "LazyVim/LazyVim",
    opts = {
      autocmds = {
        spell_check = {
          {
            event = "FileType",
            pattern = { "markdown", "text", "gitcommit" },
            callback = function()
              vim.opt_local.spell = true
              vim.opt_local.spelllang = { "en_gb" }
            end,
          },
        },
      },
    },
  },
}
