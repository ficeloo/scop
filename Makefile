# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: tcros <tcros@student.42.fr>                +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/06/16 11:49:09 by tcros             #+#    #+#              #
#    Updated: 2026/10/21 12:28:02 by tcros            ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

### VARIABLES ###
# NOM #
EXEC	= scop

# COMPILATION #
CMPL	= cargo
RFLAG	= --release

### COULEURS ###
GREEN	= \033[3;32m
RED		= \033[0;31m
ORANGE	= \033[1;33m
BLUE	= \033[0;34m
NC		= \033[0m

### REGLES D'INFERENCES ###
# REGLES PHONY #
.PHONY: all clean fclean re

all: $(EXEC)

$(EXEC): build
	@printf "$(BLUE)[INFO] Liaison finale de $(EXEC)...$(NC)\n"
	@printf "$(GREEN)[SUCCÈS] $(EXEC) compilé avec succès. ✅\n$(NC)"

build:
	@printf "$(BLUE)[INFO] Build de $(EXEC)...$(NC)\n"
	@$(CMPL) build $(RFLAG)

run:
	@printf "$(ORANGE)[INFO] Run direct de $(EXEC)...$(NC)\n"
	@$(CMPL) run $(RFLAG)

test:
	@printf "$(BLUE)[INFO] Test du projet $(EXEC)...$(NC)\n"
	@$(CMPL) test

fix:
	@printf "$(BLUE)[INFO] Fix par le compilateur du projet $(EXEC)...$(NC)\n"
	@printf "$(ORANGE)Le fix modifie automatiquement les fichiers concernés.$(NC)\n"
	@read -p "Voulez-vous procéder ? [y/N] : " ans && [ $${ans:-N} = y ] || (echo "Opération annulée."; exit 1)
	@$(CMPL) clippy --fix --allow-dirty
	@printf "$(GREEN)Fix effectué avec succès !$(NC)\n"

clean:
	@$(CMPL) clean
	@printf "$(ORANGE)[CLEAN] Fichiers target supprimés.$(NC)\n"

fclean: clean
	@rm -rf $(EXEC)
	@printf "$(RED)[FCLEAN] binaire supprimé.$(NC)\n"

re: fclean all
