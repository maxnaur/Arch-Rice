-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

-- enable true color
-- vim.opt.termguicolors = true
vim.cmd("colorscheme catppuccin")

-- no background color
vim.o.winblend = 0

vim.api.nvim_set_hl(0, "Normal", { bg = "NONE", ctermbg = "NONE" })
vim.api.nvim_set_hl(0, "NormalNC", { bg = "NONE", ctermbg = "NONE" })
vim.api.nvim_set_hl(0, "SignColumn", { bg = "NONE", ctermbg = "NONE" })
vim.api.nvim_set_hl(0, "EndOfBuffer", { bg = "NONE", ctermbg = "NONE" })
vim.api.nvim_set_hl(0, "NonText", { bg = "NONE", ctermbg = "NONE" })

-- enable wrap around
vim.opt.wrap = true
vim.opt.linebreak = true
vim.opt.breakindent = true

vim.api.nvim_create_augroup("WrapConfigs", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
  group = "WrapConfigs",
  pattern = { "conf", "config", "gitcommit", "gitrebase" },
  callback = function()
    vim.opt_local.wrap = true
    vim.opt_local.linebreak = true
    vim.opt_local.breakindent = true
  end,
})
