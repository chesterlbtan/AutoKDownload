import glob
import os
import shutil
from typing import List

from data.settings import DOWNLOAD_FOLDER, FINAL_FOLDER
from anghari_db import Status, Episodes, get_session


def main():
    with get_session() as session:
        done_series: List[Status] = session.query(Status).filter(Status.status == 'done').all()
    for series in done_series:
        print(series.location)
        leaf_path = os.path.basename(series.location)
        print(leaf_path)
        new_path = os.path.join(FINAL_FOLDER, 'Korean', 'Series', leaf_path)
        print(new_path)
        if not os.path.exists(new_path):
            os.mkdir(new_path)
        with get_session() as session:
            episodes: List[Episodes] = session.query(Episodes).\
                filter(Episodes.id == series.id).\
                filter(Episodes.status == 'done').\
                all()
        print('now moving...')
        for epi in episodes:
            source = epi.location
            desti = os.path.join(new_path, os.path.basename(source))
            shutil.copy2(source, desti)
            print(f'Episode {epi.episode} SUCCESS!')
            with get_session() as session:
                session.query(Episodes).filter(Episodes.episodes_id == epi.episodes_id)\
                    .update({Episodes.location: desti, Episodes.status: 'moved'}, synchronize_session=False)
                session.commit()
            os.remove(source)
        left_items = glob.glob(series.location)
        if len(left_items) > 0:
            raise FileExistsError(f'path <{series.location}> still contains files even after moving')
        os.rmdir(series.location)

        with get_session() as session:
            session.query(Status).filter(Status.sid == series.sid).\
                update({Status.location: new_path, Status.status: 'moved'}, synchronize_session=False)
            session.commit()


if __name__ == '__main__':
    main()
