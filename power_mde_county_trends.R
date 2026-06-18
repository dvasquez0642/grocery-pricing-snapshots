#!/usr/bin/env Rscript
# ===========================================================================
# Power / MDE analysis for county-level grocery price trends
# ---------------------------------------------------------------------------
# Goal: For each NielsenIQ product category, compute the minimum detectable
#        annual price trend (MDE) at 80% power, expressed as the minimum
#        average weekly transaction count needed per county-category cell.
#
# Estimand:  annual % change in county-category-week mean log(price per unit)
# Model:     log(p_cw) = a + b*week + month_dummies + e,  e ~ AR(1)
# Output:    CSV  + console summary
# ===========================================================================

library(readxl)
library(data.table)

cat("=== County-Level Price Trend Power Analysis ===\n\n")

# ---- 0. Paths -------------------------------------------------------------
here <- getwd()
hierarchy_path <- file.path(here, "Homescan Disagg Hierarchy.xlsx")
disagg_path    <- file.path(here,
                            "Super Category - Food & Beverages (Disagg list).xlsx")
out_dir        <- file.path(here, "analysis")
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

# ---- 1. Read hierarchy -----------------------------------------------------
raw <- as.data.table(read_excel(hierarchy_path, sheet = "1-Table-1", skip = 8))
setnames(raw, c("V1","V2","V3","V4","V5","V6","V7","V8","V9",
                "V10","V11","V12","V13","V14","V15","V16")[
                  seq_len(ncol(raw))])
# Columns of interest (based on header row inspection):
#   V5 = Department, V6 = Super Category, V7 = Category, V9 = Raw Occasions
hier <- raw[!is.na(V9), .(
  department    = V5,
  supercategory = V6,
  category      = V7,
  raw_occasions = as.numeric(V9)
)]
cat(sprintf("  Hierarchy rows loaded: %d categories, %d supercategories\n",
            nrow(hier), uniqueN(hier$supercategory)))

# ---- 2. Tag Karen's Basket supercategories ---------------------------------
disagg <- as.data.table(read_excel(disagg_path, sheet = 1))
setnames(disagg, c("supercategory_disagg", "basket_flag", "basket_items")[
                    seq_len(ncol(disagg))])
basket_names <- disagg[!is.na(basket_flag) &
                         toupper(supercategory_disagg) != "SUPERCATEGORY TOTAL",
                       toupper(trimws(supercategory_disagg))]

hier[, in_basket := toupper(trimws(supercategory)) %in% basket_names]
cat(sprintf("  Karen's Basket supercategories matched: %d  (categories: %d)\n",
            uniqueN(hier[in_basket == TRUE, supercategory]),
            nrow(hier[in_basket == TRUE])))
cat(sprintf("  Total national occasions in basket: %s\n\n",
            format(hier[in_basket == TRUE, sum(raw_occasions)], big.mark = ",")))

# ---- 3. Supercategory-level aggregation ------------------------------------
sc <- hier[, .(
  n_categories  = .N,
  total_occ     = sum(raw_occasions),
  min_cat_occ   = min(raw_occasions),
  median_cat_occ = median(raw_occasions),
  in_basket     = any(in_basket)
), by = supercategory]
setorder(sc, -total_occ)

# ---- 4. Parameter grid for MDE sweep --------------------------------------
# Weekly n: average transactions per county-category-week
weekly_n_vals <- c(1, 2, 5, 10, 25, 50, 100, 250, 500)

# Time span in weeks
T_vals <- c(104L, 156L, 208L, 260L)   # 2, 3, 4, 5 years

# AR(1) autocorrelation of weekly log-price residuals
rho_vals <- c(0.0, 0.3, 0.5, 0.7)

# Transaction-level log-price SD
# 0.15 ~ single-UPC staple (standardised index)
# 0.30 ~ typical category or decent index
# 0.50 ~ heterogeneous category with UPC/size mixing (raw mean)
sigma_txn_vals <- c(0.15, 0.30, 0.50)

# Irreducible week-level SD (true price shifts not averaged away)
sigma_week_vals <- c(0.01, 0.03)

# Power target
target_power <- 0.80
alpha        <- 0.05

# Build grid
grid <- CJ(
  weekly_n   = weekly_n_vals,
  T_weeks    = T_vals,
  rho        = rho_vals,
  sigma_txn  = sigma_txn_vals,
  sigma_week = sigma_week_vals
)
cat(sprintf("  Parameter grid: %d combinations\n", nrow(grid)))

# ---- 5. Feasibility filter: zero-week coverage ----------------------------
# Under Poisson assumption, P(zero transactions in a week) = exp(-n)
# Expected nonzero weeks out of T
grid[, nonzero_weeks := T_weeks * (1 - exp(-weekly_n))]
grid[, pct_coverage  := nonzero_weeks / T_weeks]

# Require >= 77% nonzero weeks (40/52 annualised)
grid[, feasible := pct_coverage >= 40/52]

cat(sprintf("  Feasible cells (>= 77%% week coverage): %d / %d (%.0f%%)\n",
            sum(grid$feasible), nrow(grid),
            100 * mean(grid$feasible)))

# ---- 6. Analytical MDE computation ----------------------------------------
# Model: log(p_w) = a + b*week + 11 month dummies + eps
# With T observations, df = T - 13  (intercept + slope + 11 dummies)
#
# Variance of weekly mean log price:
#   sigma_w^2 = sigma_txn^2 / n  +  sigma_week^2
#
# Under AR(1) errors, the OLS slope estimator has variance:
#   Var(b_hat) = sigma_w^2 * [(X'X)^{-1} X' Omega X (X'X)^{-1}]_{slope,slope}
# where Omega is the AR(1) correlation matrix: Omega[i,j] = rho^|i-j|
#
# We compute this sandwich form exactly for each (T, rho) combination.
# This replaces the naive sqrt((1+rho)/(1-rho)) approximation, which
# is valid only for the sample mean, not for an OLS slope with covariates.

# Pre-compute the sandwich variance inflation factor for the slope
# across all (T_weeks, rho) combos we'll use. Cache to avoid recomputation.
sandwich_cache <- list()

get_slope_var_factor <- function(T_weeks, rho) {
  key <- paste(T_weeks, rho, sep = "_")
  if (!is.null(sandwich_cache[[key]])) return(sandwich_cache[[key]])

  weeks <- seq_len(T_weeks)
  # Month dummies (cycling every 52 weeks)
  month_of_week <- ((weeks - 1) %% 52) %/% 4 + 1
  month_of_week[month_of_week > 12] <- 12
  month_mat <- model.matrix(~ factor(month_of_week))[, -1]  # 11 dummies
  X <- cbind(1, weeks, month_mat)  # intercept + slope + 11 dummies

  # AR(1) correlation matrix
  # Omega[i,j] = rho^|i-j|
  Omega <- rho^abs(outer(weeks, weeks, "-"))

  # Sandwich: (X'X)^{-1} X' Omega X (X'X)^{-1}
  XtX <- crossprod(X)
  XtX_inv <- solve(XtX)
  sandwich <- XtX_inv %*% crossprod(X, Omega %*% X) %*% XtX_inv

  # We want the variance of the slope coefficient (column 2)
  # Under i.i.d., Var(b_slope) = sigma_w^2 * (X'X)^{-1}[2,2]
  # Under AR(1), Var(b_slope) = sigma_w^2 * sandwich[2,2]
  # The inflation factor is sandwich[2,2] / (X'X)^{-1}[2,2]
  # But it's cleaner to just return sandwich[2,2] and XtX_inv[2,2] separately

  result <- list(
    sandwich_var = sandwich[2, 2],  # multiply by sigma_w^2 for actual variance
    iid_var      = XtX_inv[2, 2],   # multiply by sigma_w^2 for i.i.d. variance
    df           = T_weeks - ncol(X)
  )
  sandwich_cache[[key]] <<- result
  return(result)
}

# Pre-populate cache
cat("  Pre-computing sandwich variance factors...")
for (tw in T_vals) {
  for (r in rho_vals) {
    get_slope_var_factor(tw, r)
  }
}
cat(" done.\n")

compute_mde <- function(weekly_n, T_weeks, rho, sigma_txn, sigma_week,
                         alpha = 0.05, power = 0.80) {
  # Weekly mean log-price SD
  sigma_w <- sqrt(sigma_txn^2 / weekly_n + sigma_week^2)

  # Get pre-computed sandwich variance factor
  sv <- get_slope_var_factor(T_weeks, rho)
  df <- sv$df
  if (df < 3) return(NA_real_)

  # Critical values
  t_alpha <- qt(1 - alpha/2, df)
  t_power <- qt(power, df)

  # True SE of OLS slope under AR(1) errors
  # (this is what the slope's actual sampling variability is)
  se_b_true <- sigma_w * sqrt(sv$sandwich_var)

  # MDE per week, annualised -> approximate annual % change
  # The MDE is the slope that would be detectable if we used the

  # *true* SE (sandwich SE) for inference. But in practice, OLS reports
  # i.i.d.-based SEs. If we test using OLS SEs, the actual rejection
  # probability depends on the ratio of true SE to OLS SE.
  #
  # For a conservative power screen, we want: the true slope such that
  # using OLS (which may over- or under-reject), we still achieve 80% power.
  #
  # The OLS t-statistic is: t = b_hat / se_ols
  # where se_ols = sigma_hat * sqrt((X'X)^{-1}[2,2])
  #
  # Under the alternative with true slope beta:
  #   b_hat ~ N(beta, sigma_w^2 * sandwich_var)
  #   se_ols ~ sqrt(RSS/df * (X'X)^{-1}[2,2])
  #
  # For the power screen we assume the researcher will use Newey-West
  # or sandwich SEs (as recommended). In that case, the effective SE
  # is the true SE, and the MDE formula is straightforward:
  mde_annual <- 52 * (t_alpha + t_power) * se_b_true

  # Convert from log-points to percentage
  mde_pct <- 100 * (exp(mde_annual) - 1)

  return(mde_pct)
}

grid[feasible == TRUE, mde_pct := mapply(
  compute_mde, weekly_n, T_weeks, rho, sigma_txn, sigma_week,
  MoreArgs = list(alpha = alpha, power = target_power)
)]

# Verdict bands
grid[feasible == TRUE, verdict := fcase(
  mde_pct <  2, "well_powered",
  mde_pct <  5, "adequate",
  mde_pct < 10, "marginal",
  mde_pct >= 10, "underpowered",
  default = NA_character_
)]
grid[feasible == FALSE, verdict := "infeasible"]

cat(sprintf("  MDE computed for %d feasible cells\n\n",
            sum(!is.na(grid$mde_pct))))

# ---- 7. Minimum viable weekly n lookup table ------------------------------
# For each (T, rho, sigma_txn, sigma_week), find the smallest weekly_n
# that achieves MDE < 2%, < 5%, < 10%

thresholds <- c(2, 5, 10)
min_n_list <- list()

for (thresh in thresholds) {
  tmp <- grid[feasible == TRUE & mde_pct < thresh,
              .(min_weekly_n = min(weekly_n)),
              by = .(T_weeks, rho, sigma_txn, sigma_week)]
  tmp[, mde_threshold := thresh]
  min_n_list[[as.character(thresh)]] <- tmp
}
min_n_table <- rbindlist(min_n_list)
setorder(min_n_table, sigma_txn, rho, T_weeks, mde_threshold)

# ---- 8. Map to actual categories ------------------------------------------
# For each supercategory, compute what county share would be needed to reach
# various weekly_n values, given their national total_occ
# county_share = weekly_n * 52 / total_occ

cat("---------------------------------------------------------------\n")
cat("MINIMUM VIABLE WEEKLY n  (transactions per county-category-week)\n")
cat("  to detect annual trend at 80% power, alpha = 0.05\n")
cat("---------------------------------------------------------------\n\n")

# Show a central scenario: rho=0.5, sigma_week=0.01
# Two sigma_txn scenarios: 0.15 (standardised index) and 0.50 (raw mean)
for (s_txn in c(0.15, 0.30, 0.50)) {
  label <- if (s_txn == 0.15) "Standardised price index (sigma_txn=0.15)" else
           if (s_txn == 0.30) "Typical category (sigma_txn=0.30)" else
                              "Raw category mean / heterogeneous (sigma_txn=0.50)"
  cat(sprintf("\n--- %s ---\n", label))
  cat(sprintf("%-8s %-6s | %12s %12s %12s\n",
              "T_weeks", "rho", "MDE<2%/yr", "MDE<5%/yr", "MDE<10%/yr"))
  cat(paste(rep("-", 65), collapse = ""), "\n")

  for (tw in T_vals) {
    for (r in rho_vals) {
      vals <- sapply(thresholds, function(th) {
        row <- min_n_table[sigma_txn == s_txn & sigma_week == 0.01 &
                             T_weeks == tw & rho == r & mde_threshold == th]
        if (nrow(row) == 0) return("> 500") else return(as.character(row$min_weekly_n))
      })
      cat(sprintf("%-8d %-6.1f | %12s %12s %12s\n", tw, r,
                  vals[1], vals[2], vals[3]))
    }
  }
}

# ---- 9. Category feasibility at illustrative county sizes -----------------
cat("\n\n=============================================================\n")
cat("CATEGORY FEASIBILITY SUMMARY (Karen's Basket supercategories)\n")
cat("=============================================================\n")
cat("Central scenario: rho=0.5, sigma_week=0.01, T=104 weeks (2 yr)\n")
cat("County share scenarios: 0.5%, 0.1%, 0.02% of national panel\n\n")

shares <- c(0.005, 0.001, 0.0002)
share_labels <- c("Large metro (0.5%)", "Mid-size (0.1%)", "Small/rural (0.02%)")

basket_sc <- sc[in_basket == TRUE]

for (s_txn in c(0.15, 0.30, 0.50)) {
  label <- if (s_txn == 0.15) "Standardised index (sigma_txn=0.15)" else
           if (s_txn == 0.30) "Typical category (sigma_txn=0.30)" else
                              "Raw mean / heterogeneous (sigma_txn=0.50)"
  cat(sprintf("\n--- %s ---\n", label))
  cat(sprintf("%-40s %10s | %22s %22s %22s\n",
              "Supercategory", "Natl Occ",
              share_labels[1], share_labels[2], share_labels[3]))
  cat(paste(rep("-", 130), collapse = ""), "\n")

  for (i in seq_len(nrow(basket_sc))) {
    row <- basket_sc[i]
    vals <- character(3)
    for (j in seq_along(shares)) {
      wn <- row$total_occ * shares[j] / 52
      if (wn < 1.6) {
        vals[j] <- sprintf("n=%.1f INFEASIBLE", wn)
      } else {
        m <- compute_mde(weekly_n = wn, T_weeks = 104, rho = 0.5,
                         sigma_txn = s_txn, sigma_week = 0.01)
        verd <- if (is.na(m)) "NA" else
                if (m < 2)  sprintf("%.1f%% well_powered", m) else
                if (m < 5)  sprintf("%.1f%% adequate", m) else
                if (m < 10) sprintf("%.1f%% marginal", m) else
                            sprintf("%.1f%% underpowered", m)
        vals[j] <- verd
      }
    }
    cat(sprintf("%-40s %10s | %22s %22s %22s\n",
                substr(row$supercategory, 1, 40),
                format(row$total_occ, big.mark = ","),
                vals[1], vals[2], vals[3]))
  }
}

# ---- 10. Simulation validation --------------------------------------------
cat("\n\n=============================================================\n")
cat("SIMULATION VALIDATION\n")
cat("=============================================================\n")
cat("Checking analytical MDE against empirical rejection rates\n")
cat("(1000 replications per scenario, subset of parameter combos)\n\n")

set.seed(42)
n_sim <- 1000L

# Test a few representative combos
sim_combos <- data.table(
  weekly_n  = c(10,  50,  100, 25),
  T_weeks   = c(52, 104,  156, 52),
  rho       = c(0.0, 0.5, 0.7, 0.3),
  sigma_txn = c(0.30, 0.30, 0.15, 0.50),
  sigma_week = c(0.01, 0.01, 0.01, 0.03)
)

for (sc_i in seq_len(nrow(sim_combos))) {
  p <- sim_combos[sc_i]

  # Analytical MDE using sandwich variance
  sigma_w <- sqrt(p$sigma_txn^2 / p$weekly_n + p$sigma_week^2)
  sv <- get_slope_var_factor(p$T_weeks, p$rho)
  df <- sv$df
  t_a <- qt(1 - alpha/2, df)
  t_p <- qt(target_power, df)
  se_b_true <- sigma_w * sqrt(sv$sandwich_var)
  mde_slope <- (t_a + t_p) * se_b_true   # per-week slope in log-points

  # Simulate under the alternative (true slope = mde_slope)
  weeks <- seq_len(p$T_weeks)
  # Month dummies (cycling every 52 weeks)
  month_of_week <- ((weeks - 1) %% 52) %/% 4 + 1
  month_of_week[month_of_week > 12] <- 12
  month_mat <- model.matrix(~ factor(month_of_week))[, -1]  # 11 dummies
  Xfull <- cbind(1, weeks, month_mat)
  XtX_inv <- solve(crossprod(Xfull))

  # Pre-compute AR(1) correlation matrix for sandwich SE in simulation
  Omega_sim <- (p$rho)^abs(outer(weeks, weeks, "-"))

  rejections <- 0L
  for (sim in seq_len(n_sim)) {
    # Generate AR(1) errors
    eps <- numeric(p$T_weeks)
    eps[1] <- rnorm(1, 0, sigma_w)
    for (t in 2:p$T_weeks) {
      eps[t] <- p$rho * eps[t-1] + rnorm(1, 0, sigma_w * sqrt(1 - p$rho^2))
    }
    # Add seasonal component (small sinusoidal)
    seasonal <- 0.02 * sin(2 * pi * weeks / 52)
    # Observed log-price
    y <- mde_slope * weeks + seasonal + eps

    # OLS with month dummies
    fit <- lm.fit(Xfull, y)
    coefs <- fit$coefficients
    resids <- fit$residuals

    # Sandwich SE (Newey-West style, using known Omega structure)
    # Var(b_hat) = (X'X)^{-1} X' diag(e)*Omega*diag(e) X (X'X)^{-1}
    # For the power check, use the "known Omega" sandwich since we know
    # the true DGP. This matches the analytical formula.
    # Estimate sigma_w from residuals
    sigma_hat <- sqrt(sum(resids^2) / df)
    sandwich_se <- sigma_hat * sqrt(
      (XtX_inv %*% crossprod(Xfull, Omega_sim %*% Xfull) %*% XtX_inv)[2, 2]
    )
    t_stat <- coefs[2] / sandwich_se
    if (abs(t_stat) > qt(1 - alpha/2, df)) rejections <- rejections + 1L
  }

  empirical_power <- rejections / n_sim
  mde_pct_val <- 100 * (exp(52 * mde_slope) - 1)
  cat(sprintf(
    "  n=%3d  T=%3d  rho=%.1f  sigma_txn=%.2f  sigma_week=%.2f\n",
    p$weekly_n, p$T_weeks, p$rho, p$sigma_txn, p$sigma_week))
  cat(sprintf(
    "    Analytical MDE: %.2f%%/yr  |  Empirical power at MDE: %.1f%%  (target: 80%%)\n\n",
    mde_pct_val, 100 * empirical_power))
}

# ---- 11. Write CSV output -------------------------------------------------
out_file <- file.path(out_dir, "power_mde_county_trends.csv")
fwrite(grid, out_file)
cat(sprintf("\nFull grid written to: %s  (%d rows)\n", out_file, nrow(grid)))

min_n_file <- file.path(out_dir, "power_min_viable_n.csv")
fwrite(min_n_table, min_n_file)
cat(sprintf("Min-viable-n lookup written to: %s  (%d rows)\n", min_n_file,
            nrow(min_n_table)))

cat("\n=== Done ===\n")
