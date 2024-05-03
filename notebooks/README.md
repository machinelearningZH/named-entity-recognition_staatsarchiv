# Training a new model

1. Create env (conda, virtualenv) and install requirements with pip (!)
2. Start TEI Publisher instance with annotated XML documents (**Warning**: Make sure that the CLI client is **not** running/suspended, as it will erase all documents unless the owner is different from the credentials specified in the `.env` of the client.) To add the annotated XML documents see the video file_management_eXide_tp_training.mp4 [^1]. The user 'stazh' has to be changed bzw. deleted (see existdb_delete_stazh_for_train_annotation_teipublisher.pdf [^2]). Use source start_train / source stop_train instead of source start/source stop. 
3. Modify `get_training_data/get_training_data.ipynb` as needed (tagset, etc.) and run, which both exports XMLs from the database and a shuffled HuggingFace Dataset as `.parquet` for training or fine-tuning a HF model. Note that TEI Publisher exports paragraphs, not sentences, which can overrun SpanMarker's subtoken limit (a warning and statistics are issued during training if this happens).
4. Repeat as needed to produce additional datasets that you want to evaluate separately.
5. Copy Parquet file(s) into `training`
6. Modify `cv.ipynb` as needed and run to generate models per CV fold (folds IDs are sequential, not randomly sampled).
7. Modify `cv_baseline_evaluation.ipynb` as needed and run to get results on the same folds for a pre-trained model baseline.
8. Modify `cv_model_evaluation.ipynb` as needed and run to apply previously trained models to their corresponding test split and to obtain metrics per fold, aggregated across folds and aggregated per sub-dataset (in case of multiple datasets).
9. (Optional: Modify `training.ipynb` as needed and run to train a model on the full dataset.)

[^1]: Note: Internal documentation.
[^2]: Note: Internal documentation.
