export VCS_RUN=the/directory/of/vrun/script
export REPO_BASE=the/directory/of/repo

alias vrun="python3 $VCS_RUN/vrun.py"
alias mcdf="vrun -cfg $REPO_BASE/the/directory/of/yaml -o $REPO_BASE/out"
alias cdo="cd $REPO_BASE/out"
