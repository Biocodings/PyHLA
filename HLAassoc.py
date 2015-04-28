#!/usr/bin/env python

from __future__ import division
import scipy.stats
import math
import random
import HLAcount

def adjustP(pvalues, method = "Benjamini-Hochberg"):                
	"""                                                                                                   
	correct p-values for multiple testing
	methods: Bonferroni, Bonferroni-Holm or Holm, Benjamini-Hochberg or FDR
	"""
	n = len(pvalues)
	cp = [1]*n
	if method == "Bonferroni":
		cp = map(lambda x:min(x*n,1.0), pvalues)
	elif method == "Bonferroni-Holm" or method == "Holm":
		values = [ (pvalue, i) for i, pvalue in enumerate(pvalues) ]
		values = sorted(values)
		for rank, vals in enumerate(values):
			pvalue, i = vals
			cp[i] = (n-rank) * pvalue
		for rank, vals in enumerate(values):
			pvalue, i = vals                                                      
			if rank > 0:
				cp[i] = min(1.0, max(cp[i], cp[j]))
			else:
				cp[i] = min(1.0, cp[i])
			j = i
	elif method == "Benjamini-Hochberg" or method == "FDR":
		values = [ (pvalue, i) for i, pvalue in enumerate(pvalues) ]
		values = sorted(values,reverse=True)
		for rank, vals in enumerate(values):
			pvalue, i = vals
			cp[i] = n * pvalue / (n-rank)
		for rank, vals in enumerate(values):
			pvalue, i = vals
			if rank > 0:
				cp[i] = min(1.0, min(cp[i], cp[j]))
			else:
				cp[i] = min(1.0, cp[i])
			j = i
	elif method == "Benjamini-Yekutieli" or method == "FDR_BY":
		q = 0
		for i in range(1,n+1):
			q += 1.0 / i
		values = [ (pvalue, i) for i, pvalue in enumerate(pvalues) ]
		values = sorted(values,reverse=True)
		for rank, vals in enumerate(values):
			pvalue, i = vals
			cp[i] = q * pvalue * n/(n-rank)
		for rank, vals in enumerate(values):
			pvalue, i = vals
			if rank > 0:
				cp[i] = min(1.0, min(cp[i], cp[j]))
			else:
				cp[i] = min(1.0, cp[i])
			j = i
	return cp
def assocADRChiFisher(infile, digit, freq, test='chisq', model = 'allelic', adjust='FDR', exclude=None, perm=None, seed=None):
	'''
	Association Analysis for Allelic, Dominant or Recessive Model
	Pearson's Chi-squared test or Fisher exact test
	return allele counts, frequency, [chi-square, df,] p, and OR, adjustedP, permutationP
	'''
	if model == 'allelic':
		caseAlleles, ctrlAlleles, np, nc, nn = HLAcount.allelicCount(infile, digit)
	elif model == 'dom':
		caseAlleles, ctrlAlleles, np, nc, nn = HLAcount.domCount(infile, digit)
	elif model == 'rec':
		caseAlleles, ctrlAlleles, np, nc, nn = HLAcount.recCount(infile, digit)
	alleleFreq, alleles = HLAcount.hlaFreq(caseAlleles, ctrlAlleles, np, nc, nn)

	excludeAlleles =[]
	if exclude is not None:
		ef = open(exclude)
		for line in ef:
			line = line.strip()
			excludeAlleles.append(line)
		ef.close()

	usedAllele = []
	assoc = {}
	for allele in caseAlleles.keys():
		if allele in ctrlAlleles:
			if allele not in excludeAlleles:
				if (alleleFreq[allele][2]) > freq:
					usedAllele.append(allele)
					n1 = caseAlleles[allele]
					n2 = np[allele.split('*')[0]] - n1
					n3 = ctrlAlleles[allele]
					n4 = nc[allele.split('*')[0]] - n3
					data = [[n1, n2], [n3, n4]]
					if test == "chisq":
						chi2, p, dof, expected = scipy.stats.chi2_contingency(data)
					OR, pvalue = scipy.stats.fisher_exact(data)
					se = math.sqrt(1.0/n1  + 1.0/n2 +  1.0/n3 + 1.0/n4)
					l95 = math.exp(math.log(OR) - 1.96 * se)
					u95 = math.exp(math.log(OR) + 1.96 * se)
					ss = []
					ss.append(n1)
					ss.append(n2)
					ss.append(n3)
					ss.append(n4)
					ss.append(alleleFreq[allele][0])
					ss.append(alleleFreq[allele][1])
					ss.append(alleleFreq[allele][2])	
					if test == "chisq":
						ss.append(p)
						ss.append(chi2)
						ss.append(dof)
					elif test == "fisher":
						ss.append(pvalue)
					ss.append(OR)
					ss.append(l95)
					ss.append(u95)
					assoc[allele] = ss
	### adjust
	genes = []
	for g in np.keys():
		if g in nc.keys():
			genes.append(g)
	for g in sorted(genes):      ### GENE BY GENE
		ps = []
		ns = []
		for a in assoc:
			if a.startswith(g) and assoc[a][7] != 'NA':  # p value at 7 col start from 0
				ps.append(assoc[a][7])
				ns.append(a)
		cp = adjustP(ps,adjust)
		for i in range(len(ns)):
			if assoc[ns[i]][7] != 'NA':
				assoc[ns[i]].append(cp[i])
			else:
				assoc[ns[i]].append('NA')

	if perm is None:
		return assoc
	else:
		random.seed(seed)
		permP = {}       # perm p value
		permN = {}      # perm p < orig p
		permNL = {}    # perm p > orig p
		permNA = {}    # perm NA
		for a in assoc:
			permNA[a] = 0
			permNL[a] = 0
			permN[a] = 0
		if perm > 10:
			pf = perm / 10
		else:
			pf = 2
		pn = 0   # effect perm number
		while True:
			if model == 'allelic':
				case9, ctrl9, np9, nc9, nn9 = HLAcount.allelicCount(infile,digit, True)
			elif model == 'dom':
				case9, ctrl9, np9, nc9, nn9 = HLAcount.domCount(infile,digit, True)
			elif model == 'rec':
				case9, ctrl9, np9, nc9, nn9 = HLAcount.recCount(infile,digit, True)
			ca = []   # current alleles
			for a in case9:
				if a in ctrl9:
					ca.append(a)
			if set(usedAllele) <= set(ca):  # current alleles contain used allele
	        		for a in usedAllele:
					n1 = case9[a]
					n2 = np9[a.split('*')[0]] - n1
					n3 = ctrl9[a]
					n4 = nc9[a.split('*')[0]] - n3
					data = [[n1, n2], [n3, n4]]
					if test == "chisq":
						chi2, p, dof, expected = scipy.stats.chi2_contingency(data)
					elif test == 'fisher':
						OR, p = scipy.stats.fisher_exact(data)
					if not isinstance(p, float):
						permNA[a] += 1
					else:
						if assoc[a][7] == 'NA':
							permNA[a] += 1
						else:
							if p < assoc[a][7]:
								permN[a] += 1
							else:
								permNL[a] += 1
				pn += 1
				if pn % pf == 1:
					print 'permutation {}/{} ...'.format(pn, perm)
			if pn == perm:
				break
		for a in assoc:
			if assoc[a][7] == 'NA':
				permP[a] = 'NA'
			else:
				if permNA[a] == perm:
					permP[a] = 'NA'
				else:
					permP[a] = 1.0 * (permN[a] + 1) / (perm + 1 - permNA[a])
		return assoc, permP, permN, permNA, permNL
def assocRaw(infile, digit, freq, exclude=None, perm=None, seed=None):
	'''
	Association Analysis (2 x m)
	Pearson's Chi-squared test
	return chi-square, df, p
	'''
	caseAlleles, ctrlAlleles, np, nc, nn = HLAcount.allelicCount(infile, digit)
	alleleFreq, alleles = HLAcount.hlaFreq(caseAlleles, ctrlAlleles, np, nc, nn)
	assoc = {}
	usedAllele = []

	excludeAlleles =[]
	if exclude is not None:
		ef = open(exclude)
		for line in ef:
			line = line.strip()
			excludeAlleles.append(line)
		ef.close()

	### genes
	gene = []  # get all genes name
	for a in np:
		if a in nc:
			gene.append(a)

	for g in gene:
		n1 = []
		n2 = []
		for a in caseAlleles:
			if a in ctrlAlleles:
				if a.startswith(g):
					if alleleFreq[a][2] > freq:
						n1.append(caseAlleles[a])
						n2.append(ctrlAlleles[a])
						usedAllele.append(a)
		data = [n1, n2]
		chi2, p, dof, expected = scipy.stats.chi2_contingency(data)
		ss = []
		if not isinstance(chi2, float):
			ss.append('NA')
		else:
			ss.append(chi2)
		if not isinstance(dof, int):
			ss.append('NA')
		else:
			ss.append(dof)
		if not isinstance(p, float):
			ss.append('NA')
		else:
			ss.append(p)
		assoc[g] = ss
	if perm is None:
		return assoc, usedAllele
	else:
		random.seed(seed)
		permP = {}       # perm p value
		permN = {}      # perm p < orig p
		permNL = {}    # perm p > orig p
		permNA = {}    # perm NA
		for a in assoc:
			permNA[a] = 0
			permNL[a] = 0
			permN[a] = 0
		if perm > 10:
			pf = perm / 10
		else:
			pf = 2
		pn = 0   # effect perm number
		while True:
			case9, ctrl9, np9, nc9, nn9 = HLAcount.allelicCount(infile,digit, True)
			ca = []   # current alleles
			for a in case9:
				if a in ctrl9:
					ca.append(a)
			if set(usedAllele) <= set(ca):  # current alleles contain used allele
	        		for g in gene:
					n1 = []
					n2 = []
					for a in case9:
						if a in ctrl9:
							if a.startswith(g):
								n1.append(case9[a])
								n2.append(ctrl9[a])

					data = [n1, n2]
					chi2, p, dof, expected = scipy.stats.chi2_contingency(data)
					if not isinstance(p, float):
						permNA[g] += 1
					else:
						if assoc[g][2] == 'NA':
							permNA[g] += 1
						else:
							if p < assoc[g][2]:
								permN[g] += 1
							else:
								permNL[g] += 1
				pn += 1
				if pn % pf == 1:
					print 'permutation {}/{} ...'.format(pn, perm)
			if pn == perm:
				break
		for a in assoc:
			if assoc[a][2] == 'NA':
				permP[a] = 'NA'
			else:
				if permNA[a] == perm:
					permP[a] = 'NA'
				else:
					permP[a] = 1.0 * (permN[a] + 1) / (perm + 1 - permNA[a])
		return assoc, usedAllele, permP, permN, permNA, permNL
def assocScoreU(caseAlleles, ctrlAlleles, np, nc, freq, test):
	'''
	Association Analysis (2 x m)
	Score test
	return score test U
	'''
	assoc = {}
	### genes
	gene = {}  # get all genes name
	for a in caseAlleles:
		temp = a.split('*')
		gene[temp[0]] = 1
	for g in gene:
		### counts
		case = {}
		ctrl = {}
		for a in caseAlleles:
			if a.startswith(g):
				case[a] = caseAlleles[a]
		for a in ctrlAlleles:
			if a.startswith(g):
				ctrl[a] = ctrlAlleles[a]
		### freq
		freqCase = {}
		freqCtrl = {}
		freqAll = {}
		n1 = 0
		n2 = 0
		for a in case:
			freqCase[a] = 1.0 * case[a] / np[g]
		for a in ctrl:
			freqCtrl[a] = 1.0 * ctrl[a] / nc[g]
			if a in case:
				freqAll[a] = 1.0 * (case[a] + ctrl[a]) / (np[g] + nc[g])
		### score test U
		n1 = np[g]
		u = 0
		for a in freqAll:
			# if freqCase[a] > freq or freqCtrl[a] > freq:
			if freqAll[a] > freq:
				u = u + (case[a] - n1 * freqAll[a]) ** 2 / freqAll[a] - (case[a] - n1 * freqAll[a]) / freqAll[a]
		if not isinstance(u, float):
			u = 'NA'
		assoc[g] = u
	return assoc