#!/bin/bash

# Cherche glslc dans le PATH, puis dans ~/.local/bin (postes de 42).
if command -v glslc >/dev/null 2>&1; then
	GLSLC="glslc"
elif [ -x "$HOME/.local/bin/glslc" ]; then
	GLSLC="$HOME/.local/bin/glslc"
else
	GLSLC=""
fi

if [ -n "$GLSLC" ]; then
	"$GLSLC" shader.vert -o vert.spv && "$GLSLC" shader.frag -o frag.spv
elif [ -f vert.spv ] && [ -f frag.spv ]; then
	echo "glslc introuvable : utilisation des shaders précompilés (.spv)."
else
	echo "Erreur : glslc introuvable et aucun shader précompilé." >&2
	exit 1
fi
