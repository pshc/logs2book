all: mmm.log.pdf

%.log.pdf: %.log.tex
	pdflatex $<

%.log.tex: %.log convert.py
	./convert.py $<

clean:
	rm *.aux *.log.log
